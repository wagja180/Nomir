"""اختبار الاستراتيجية على بيانات تاريخية قبل استخدامها."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import symbols
from .candles import Candle
from .strategy import TrendMomentumStrategy


@dataclass
class Trade:
    side: str
    entry_time: int
    entry: float
    sl: float
    tp: float
    exit_time: int | None = None
    exit: float | None = None
    r_multiple: float = 0.0
    pnl: float = 0.0


@dataclass
class BacktestResult:
    symbol: str
    trades: list[Trade] = field(default_factory=list)
    equity: list[float] = field(default_factory=list)
    start_balance: float = 10000.0

    def stats(self) -> dict:
        n = len(self.trades)
        if n == 0:
            return {"trades": 0}
        pnl = [t.pnl for t in self.trades]
        wins = sum(x for x in pnl if x > 0)
        losses = -sum(x for x in pnl if x <= 0)
        peak, dd = self.start_balance, 0.0
        for v in self.equity:
            peak = max(peak, v)
            dd = min(dd, (v - peak) / peak)
        return {
            "trades": n,
            "win_rate_%": round(100 * sum(1 for x in pnl if x > 0) / n, 1),
            "profit_factor": round(wins / losses, 2) if losses else float("inf"),
            "net_profit": round(sum(pnl), 2),
            "return_%": round(100 * sum(pnl) / self.start_balance, 2),
            "max_drawdown_%": round(100 * dd, 2),
            "avg_R": round(sum(t.r_multiple for t in self.trades) / n, 2),
        }


def run_backtest(candles: list[Candle], symbol: str, strategy: TrendMomentumStrategy | None = None,
                 balance: float = 10000.0, risk_pct: float = 1.0, spread_pips: float = 1.0) -> BacktestResult:
    """يدخل عند افتتاح الشمعة التالية للإشارة؛ إن لمست الشمعة الوقف والهدف معاً نحتسب الوقف.

    الأسعار التاريخية أسعار وسطية: الشراء يُفتح بسعر الطلب (ask) ويُغلق بسعر العرض (bid)،
    والعكس للبيع، فيُحتسب السبريد كتكلفة حقيقية في كل صفقة.
    """
    strategy = strategy or TrendMomentumStrategy()
    d = strategy.prepare(candles)
    spread = spread_pips * symbols.pip_size(symbol)
    half = spread / 2
    res = BacktestResult(symbol, start_balance=balance)
    open_t: Trade | None = None
    risk_amt = 0.0
    c = candles

    i = 0
    while i < len(c) - 1:
        if open_t is None:
            sig = strategy.signal_at(d, i, symbol)
            if sig:
                j = i + 1
                sgn = 1 if sig.side == "BUY" else -1
                entry = c[j].open + sgn * half
                dist = abs(sig.entry - sig.stop_loss)
                open_t = Trade(sig.side, c[j].time, entry, entry - sgn * dist,
                               entry + sgn * dist * strategy.p["rr"])
                risk_amt = balance * risk_pct / 100
                i = j
                continue
        else:
            sgn = 1 if open_t.side == "BUY" else -1
            # الشراء يُغلق بسعر العرض (الوسط - نصف السبريد)، والبيع بسعر الطلب (الوسط + نصفه)
            lo, hi = c[i].low - sgn * half, c[i].high - sgn * half
            hit_sl = lo <= open_t.sl if sgn > 0 else hi >= open_t.sl
            hit_tp = hi >= open_t.tp if sgn > 0 else lo <= open_t.tp
            if hit_sl or hit_tp:
                px = open_t.sl if hit_sl else open_t.tp
                r = sgn * (px - open_t.entry) / abs(open_t.entry - open_t.sl)
                open_t.exit, open_t.exit_time, open_t.r_multiple = px, c[i].time, r
                open_t.pnl = r * risk_amt
                balance += open_t.pnl
                res.trades.append(open_t)
                open_t = None
        res.equity.append(balance)
        i += 1
    return res
