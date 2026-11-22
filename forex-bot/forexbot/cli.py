"""واجهة سطر الأوامر.

  python -m forexbot scan       فحص الأزواج الآن وعرض الفرص
  python -m forexbot news       عرض الأخبار والأحداث الاقتصادية القادمة
  python -m forexbot run        تشغيل البوت بشكل مستمر
  python -m forexbot backtest   اختبار الاستراتيجية تاريخياً
  python -m forexbot status     الرصيد والصفقات (وضع المحاكاة)
  python -m forexbot optimize   تجربة عدة إعدادات وعرض أفضلها
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import yaml

from .backtest import run_backtest
from .candles import fmt_time
from .bot import ForexBot, format_signal
from .data import make_provider
from .strategy import TrendMomentumStrategy


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def optimize(cfg: dict, syms: list[str], tfs: list[str]) -> None:
    """يجرب عدة إعدادات (الإطار، قوة الإشارة، العائد/المخاطرة) ويرتب النتائج."""
    provider = make_provider(cfg.get("data", {}))
    risk = cfg.get("risk", {})
    spread = cfg.get("paper", {}).get("spread_pips", 1.0)
    rows = []
    for sym in syms:
        for tf in tfs:
            try:
                candles = provider.candles(sym, tf, 100000)
            except Exception as e:
                print(f"تعذّر جلب {sym} {tf}: {e}")
                continue
            base = TrendMomentumStrategy(cfg.get("strategy"))
            prepared = base.prepare(candles)  # المؤشرات لا تتغير بين التجارب
            print(f"... {sym} {tf}", flush=True)
            for ms in (50, 60, 70, 80):
                for rr in (1.5, 2.0, 3.0):
                    strat = TrendMomentumStrategy({**(cfg.get("strategy") or {}), "min_score": ms, "rr": rr})
                    st = run_backtest(candles, sym, strat, risk_pct=risk.get("risk_per_trade_pct", 1.0),
                                      spread_pips=spread, max_trades_per_day=risk.get("max_trades_per_day", 0),
                                      prepared=prepared).stats()
                    if st.get("trades", 0) >= 20:
                        rows.append((sym, tf, ms, rr, st))
    rows.sort(key=lambda r: -r[4]["profit_factor"])
    print("\nالزوج    الإطار القوة  R:R  صفقات/يوم  معامل الربح  العائد%  التراجع%")
    for sym, tf, ms, rr, st in rows[:25]:
        flag = "✅" if st["profit_factor"] >= 1.2 and st["max_drawdown_%"] > -20 else "  "
        print(f"{flag}{sym:8} {tf:4} {ms:4} {rr:4.1f}   {st['trades_per_day']:6.2f}    {st['profit_factor']:6.2f}"
              f"   {st['return_%']:7.1f}  {st['max_drawdown_%']:7.1f}")
    print("\n✅ = معامل ربح ≥ 1.2 وتراجع أقل من 20%. احذر: أفضل نتيجة من عدة تجارب قد تكون صدفة.")


def print_status(cfg: dict) -> None:
    from .broker import PaperBroker
    p = cfg.get("paper", {})
    start = float(p.get("balance", 10000.0))
    b = PaperBroker(p.get("state_file", "paper_state.json"), start)
    closed = b.history
    wins = sum(1 for t in closed if t.pnl > 0)
    print("💼 الحساب التجريبي")
    print(f"  الرصيد: {b.balance:,.2f} $   (البداية {start:,.2f} $)")
    print(f"  الربح/الخسارة المحقق: {b.balance - start:+,.2f} $")
    print(f"  الصفقات المغلقة: {len(closed)}" + (f"   الرابحة: {100 * wins / len(closed):.0f}%" if closed else ""))
    print(f"\n📂 الصفقات المفتوحة ({len(b.positions)}):")
    for t in b.positions:
        print(f"  {t.id} {t.symbol} {'شراء' if t.side == 'BUY' else 'بيع'}  دخول {t.entry:.5g}  "
              f"وقف {t.stop_loss:.5g}  هدف {t.take_profit:.5g}  ({t.opened_at[:16].replace('T', ' ')})")
    if not b.positions:
        print("  لا يوجد")
    print("\n📜 آخر الصفقات المغلقة:")
    for t in closed[-10:][::-1]:
        print(f"  {t.id} {t.symbol} {'شراء' if t.side == 'BUY' else 'بيع'}  {t.pnl:+,.2f} $  ({t.reason})")
    if not closed:
        print("  لا يوجد بعد")


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="forexbot", description="بوت تداول الفوركس")
    ap.add_argument("-c", "--config", default=os.environ.get("FOREXBOT_CONFIG", "config.yaml"))
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    n = sub.add_parser("news")
    n.add_argument("--hours", type=float, default=24)
    sub.add_parser("run")
    sub.add_parser("status")
    o = sub.add_parser("optimize")
    o.add_argument("--symbol", help="زوج أو عدة أزواج مفصولة بفاصلة، مثل XAUUSD,EURUSD")
    o.add_argument("--timeframes", default="H1,H4")
    b = sub.add_parser("backtest")
    b.add_argument("--symbol", help="زوج واحد (الافتراضي: كل الأزواج في الإعدادات)")
    b.add_argument("--timeframe", default=None)
    a = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(a.config)

    if a.cmd == "backtest":
        provider = make_provider(cfg.get("data", {}))
        strat = TrendMomentumStrategy(cfg.get("strategy"))
        tf = a.timeframe or cfg.get("timeframe", "H1")
        risk = cfg.get("risk", {}).get("risk_per_trade_pct", 1.0)
        spread = cfg.get("paper", {}).get("spread_pips", 1.0)
        for sym in ([a.symbol] if a.symbol else cfg["symbols"]):
            candles = provider.candles(sym, tf, 100000)
            if not candles:
                print(f"\n=== {sym}: لا توجد بيانات ===")
                continue
            res = run_backtest(candles, sym, strat, risk_pct=risk, spread_pips=spread,
                               max_trades_per_day=cfg.get("risk", {}).get("max_trades_per_day", 0))
            print(f"\n=== {sym} {tf}  ({fmt_time(candles[0].time, '%Y-%m-%d')} → "
                  f"{fmt_time(candles[-1].time, '%Y-%m-%d')}) ===")
            for k, v in res.stats().items():
                print(f"  {k}: {v}")
        return

    if a.cmd == "optimize":
        optimize(cfg, a.symbol.split(",") if a.symbol else cfg["symbols"], a.timeframes.split(","))
        return

    if a.cmd == "status":
        print_status(cfg)
        return

    bot = ForexBot(cfg)
    if a.cmd == "news":
        print(bot.news_report(a.hours))
    elif a.cmd == "scan":
        sigs = bot.scan()
        if not sigs:
            print("لا توجد فرص مطابقة للشروط حالياً.")
        for s in sigs:
            print(format_signal(s), "\n")
    elif a.cmd == "run":
        try:
            bot.run()
        except KeyboardInterrupt:
            print("\nتم إيقاف البوت.")
