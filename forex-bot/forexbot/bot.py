"""الحلقة الرئيسية: تتبّع الأزواج، فحص الأخبار، توليد الإشارات، التنفيذ وإدارة المخاطر."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from . import symbols
from .candles import fmt_time
from .broker import OandaBroker, PaperBroker
from .data import make_provider
from .news import NewsMonitor
from .notifier import Notifier
from .risk import RiskConfig, RiskManager, position_units
from .strategy import Signal, TrendMomentumStrategy

log = logging.getLogger(__name__)


def format_signal(sig: Signal, units: int | None = None) -> str:
    arrow = "🟢 شراء" if sig.side == "BUY" else "🔴 بيع"
    pip = symbols.pip_size(sig.symbol)
    lines = [
        f"{arrow} {sig.symbol}  | القوة {sig.score:.0f}/100",
        f"الدخول: {sig.entry:.5f}",
        f"وقف الخسارة: {sig.stop_loss:.5f} ({abs(sig.entry - sig.stop_loss) / pip:.0f} نقطة)",
        f"جني الربح: {sig.take_profit:.5f} ({abs(sig.take_profit - sig.entry) / pip:.0f} نقطة)",
        f"العائد/المخاطرة: 1:{sig.risk_reward:.1f}",
        f"وقت الشمعة: {fmt_time(sig.time)} UTC",
    ]
    if units:
        lines.append(f"الحجم: {units:,} وحدة ({units / 100000:.2f} لوت)")
    lines += ["الأسباب:"] + [f"  • {r}" for r in sig.reasons]
    return "\n".join(lines)


class ForexBot:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.provider = make_provider(cfg.get("data", {}))
        self.strategy = TrendMomentumStrategy(cfg.get("strategy"))
        self.news = NewsMonitor(cfg.get("news", {}))
        self.risk = RiskManager(RiskConfig(**cfg.get("risk", {})))
        self.notifier = Notifier(cfg.get("notify", {}).get("telegram", True))
        self.account_ccy = cfg.get("account_currency", "USD")
        self.timeframe = cfg.get("timeframe", "H1")
        mode = cfg.get("mode", "paper")
        if mode == "paper":
            p = cfg.get("paper", {})
            self.broker = PaperBroker(p.get("state_file", "paper_state.json"),
                                      p.get("balance", 10000.0), p.get("spread_pips", 1.0))
        elif mode in ("oanda_practice", "oanda_live"):
            self.broker = OandaBroker(practice=(mode == "oanda_practice"))
        elif mode == "signals":
            self.broker = None  # تنبيهات فقط بدون تنفيذ
        else:
            raise ValueError(f"وضع غير معروف: {mode}")
        self._day, self._day_start_balance = None, None
        self._last_signal_bar: dict[str, object] = {}

    # ---- مساعدات ----
    def _quote_to_account(self, symbol: str, price: float) -> float:
        base, quote = symbols.split(symbol)
        if quote == self.account_ccy:
            return 1.0
        if base == self.account_ccy:
            return 1.0 / price
        for pair, inv in ((quote + self.account_ccy, False), (self.account_ccy + quote, True)):
            try:
                px = self.provider.last_price(pair)
                return 1.0 / px if inv else px
            except Exception:
                continue
        return 1.0

    def _day_pnl(self, balance: float) -> float:
        today = datetime.now(timezone.utc).date()
        if self._day != today:
            self._day, self._day_start_balance = today, balance
        return balance - self._day_start_balance

    # ---- التقارير ----
    def news_report(self, hours: float = 24) -> str:
        self.news.refresh(force=True)
        out = [f"📅 الأحداث الاقتصادية المهمة خلال {hours:.0f} ساعة:"]
        ev = self.news.upcoming(hours, "Medium")
        if not ev:
            out.append("  لا يوجد (أو تعذّر جلب التقويم)")
        for e in ev:
            mark = "🔥" if e.impact == "High" else "⚠️"
            extra = f" | متوقع {e.forecast} سابق {e.previous}" if e.forecast or e.previous else ""
            if e.actual:
                extra += f" | فعلي {e.actual}"
            out.append(f"  {mark} {e.time:%a %H:%M} UTC  {e.currency}  {e.title}{extra}")
        curs = sorted({c for s in self.cfg["symbols"] for c in symbols.split(s)})
        out.append("\n📰 اتجاه الأخبار (آخر 12 ساعة):")
        for c in curs:
            s = self.news.sentiment(c)
            out.append(f"  {c}: {'+' if s > 0 else ''}{s} " + ("إيجابي" if s > 0 else "سلبي" if s < 0 else "محايد"))
        return "\n".join(out)

    def scan(self) -> list[Signal]:
        """فحص كل الأزواج مرة واحدة وإرجاع الإشارات."""
        self.news.refresh()
        found = []
        for sym in self.cfg["symbols"]:
            try:
                candles = self.provider.candles(sym, self.timeframe, 600)
            except Exception as e:
                log.warning("تعذّر جلب أسعار %s: %s", sym, e)
                continue
            base, quote = symbols.split(sym)
            ev = self.news.blackout((base, quote))
            if ev:
                log.info("%s: تجاهل — خبر قوي قريب: %s %s", sym, ev.currency, ev.title)
                continue
            sig = self.strategy.latest(candles, symbols.normalize(sym), self.news.pair_bias(base, quote))
            if sig:
                found.append(sig)
        return sorted(found, key=lambda s: -s.score)

    # ---- الحلقة ----
    def step(self) -> None:
        if self.broker is not None:
            for sym in self.cfg["symbols"]:
                try:
                    last = self.provider.candles(sym, "M15", 4)
                except Exception:
                    continue
                if not last:
                    continue
                px = last[-1].close
                closed = self.broker.update(sym, max(c.high for c in last), min(c.low for c in last),
                                            px, self._quote_to_account(sym, px))
                for p in closed:
                    self.notifier.send(f"✅ إغلاق {p.symbol} {p.side} ({p.reason}) الربح/الخسارة: {p.pnl:+.2f}")

        for sig in self.scan():
            if self._last_signal_bar.get(sig.symbol) == sig.time:
                continue  # لا تكرار لنفس الشمعة
            self._last_signal_bar[sig.symbol] = sig.time
            if self.broker is None:
                self.notifier.send(format_signal(sig))
                continue
            balance = float(self.broker.balance)
            opens = self.broker.open_positions()
            ok, why = self.risk.can_open(len(opens), self._day_pnl(balance), balance,
                                         any(p.symbol == sig.symbol for p in opens))
            if not ok:
                log.info("%s: لم تُفتح الصفقة — %s", sig.symbol, why)
                continue
            units = position_units(balance, self.risk.cfg.risk_per_trade_pct, sig.entry, sig.stop_loss,
                                   sig.symbol, self.account_ccy, self._quote_to_account(sig.symbol, sig.entry))
            if units < self.risk.cfg.min_units:
                log.info("%s: الحجم أصغر من الحد الأدنى", sig.symbol)
                continue
            self.broker.market_order(sig.symbol, sig.side, units, sig.stop_loss, sig.take_profit, sig.entry)
            self.notifier.send("📌 صفقة جديدة\n" + format_signal(sig, units))

    def run(self) -> None:
        every = self.cfg.get("poll_seconds", 300)
        self.notifier.send(f"🤖 بدأ البوت (الوضع: {self.cfg.get('mode', 'paper')}) — "
                           f"يتتبع {', '.join(self.cfg['symbols'])}")
        while True:
            try:
                self.step()
            except KeyboardInterrupt:
                raise
            except Exception:
                log.exception("خطأ في الدورة")
            time.sleep(every)
