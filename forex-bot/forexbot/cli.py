"""واجهة سطر الأوامر.

  python -m forexbot scan       فحص الأزواج الآن وعرض الفرص
  python -m forexbot news       عرض الأخبار والأحداث الاقتصادية القادمة
  python -m forexbot run        تشغيل البوت بشكل مستمر
  python -m forexbot backtest   اختبار الاستراتيجية تاريخياً
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
            res = run_backtest(candles, sym, strat, risk_pct=risk, spread_pips=spread)
            print(f"\n=== {sym} {tf}  ({fmt_time(candles[0].time, '%Y-%m-%d')} → "
                  f"{fmt_time(candles[-1].time, '%Y-%m-%d')}) ===")
            for k, v in res.stats().items():
                print(f"  {k}: {v}")
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
