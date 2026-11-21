"""اختبار الاستراتيجية على بيانات تاريخية قبل استخدامها."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import symbols
from .strategy import TrendMomentumStrategy


@dataclass
class Trade:
    side: str
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp: float
    exit_time: pd.Timestamp | None = None
    exit: float | None = None
    r_multiple: float = 0.0
    pnl: float = 0.0


@dataclass
class BacktestResult:
    symbol: str
    trades: list[Trade] = field(default_factory=list)
    equity: pd.Series | None = None
    start_balance: float = 10000.0

    def stats(self) -> dict:
        n = len(self.trades)
        if n == 0:
            return {"trades": 0}
        pnl = np.array([t.pnl for t in self.trades])
        wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
        eq = self.equity
        dd = ((eq - eq.cummax()) / eq.cummax()).min() * 100 if eq is not None else 0.0
        return {
            "trades": n,
            "win_rate_%": round(100 * len(wins) / n, 1),
            "profit_factor": round(wins.sum() / abs(losses.sum()), 2) if losses.sum() else float("inf"),
            "net_profit": round(pnl.sum(), 2),
            "return_%": round(100 * pnl.sum() / self.start_balance, 2),
            "max_drawdown_%": round(float(dd), 2),
            "avg_R": round(float(np.mean([t.r_multiple for t in self.trades])), 2),
        }


def run_backtest(df: pd.DataFrame, symbol: str, strategy: TrendMomentumStrategy | None = None,
                 balance: float = 10000.0, risk_pct: float = 1.0, spread_pips: float = 1.0) -> BacktestResult:
    """يدخل عند افتتاح الشمعة التالية للإشارة؛ إن لمست الشمعة الوقف والهدف معاً نحتسب الوقف."""
    strategy = strategy or TrendMomentumStrategy()
    d = strategy.prepare(df)
    spread = spread_pips * symbols.pip_size(symbol)
    res = BacktestResult(symbol, start_balance=balance)
    eq_vals, eq_idx = [], []
    open_t: Trade | None = None
    risk_amt = 0.0
    o, h, l = d["open"].values, d["high"].values, d["low"].values

    i = 0
    while i < len(d) - 1:
        if open_t is None:
            sig = strategy.signal_at(d, i, symbol)
            if sig:
                j = i + 1
                sgn = 1 if sig.side == "BUY" else -1
                entry = o[j] + sgn * spread / 2
                dist = abs(sig.entry - sig.stop_loss)
                open_t = Trade(sig.side, d.index[j], entry, entry - sgn * dist,
                               entry + sgn * dist * strategy.p["rr"])
                risk_amt = balance * risk_pct / 100
                i = j
                continue
        else:
            sgn = 1 if open_t.side == "BUY" else -1
            hit_sl = l[i] <= open_t.sl if sgn > 0 else h[i] >= open_t.sl
            hit_tp = h[i] >= open_t.tp if sgn > 0 else l[i] <= open_t.tp
            if hit_sl or hit_tp:
                px = open_t.sl if hit_sl else open_t.tp
                r = sgn * (px - open_t.entry) / abs(open_t.entry - open_t.sl)
                open_t.exit, open_t.exit_time, open_t.r_multiple = px, d.index[i], r
                open_t.pnl = r * risk_amt
                balance += open_t.pnl
                res.trades.append(open_t)
                open_t = None
        eq_vals.append(balance)
        eq_idx.append(d.index[i])
        i += 1
    res.equity = pd.Series(eq_vals, index=eq_idx)
    return res
