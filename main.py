"""نقطة الدخول الرئيسية لبوت تحليل السوق ومناطق البيع/الشراء.

أمثلة استخدام:
  python main.py analyze --symbol BTC/USDT --timeframe 4h
  python main.py backtest --symbol BTC/USDT --timeframe 4h --candles 1000
  python main.py trade --symbol BTC/USDT --timeframe 1h              # تجربة فقط (dry-run)
  python main.py trade --symbol BTC/USDT --timeframe 1h --live --confirm   # تنفيذ حقيقي
"""

import argparse
import logging
import sys

from bot.config import config
from bot.data_fetcher import build_exchange, fetch_ohlcv
from bot.executor import execute_signal
from bot.indicators import add_indicators
from bot.report import plot_chart, text_report
from bot.risk import compute_position_size
from bot.signals import generate_signal
from bot.zones import detect_zones

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot.main")


def _prepare(symbol: str, timeframe: str, candles: int):
    exchange = build_exchange()
    df = fetch_ohlcv(exchange, symbol, timeframe=timeframe, limit=candles)
    df = add_indicators(df)
    zones = detect_zones(df)
    signal = generate_signal(df, zones)
    return exchange, df, zones, signal


def cmd_analyze(args):
    exchange, df, zones, signal = _prepare(args.symbol, args.timeframe, args.candles)
    price = float(df.iloc[-1]["close"])

    report = text_report(args.symbol, args.timeframe, zones, signal, price)
    print(report)

    out_path = args.chart_out or f"reports/{args.symbol.replace('/', '_')}_{args.timeframe}.png"
    try:
        plot_chart(df, zones, args.symbol, signal, out_path)
        print(f"\nتم حفظ الرسم البياني في: {out_path}")
    except ImportError:
        print(
            "\n(تعذّر إنشاء الرسم البياني لأن مكتبة matplotlib غير مثبتة — التقرير النصي أعلاه كافٍ "
            "للتحليل. لتفعيل الرسم البياني ثبّت matplotlib ثم أعد التشغيل.)"
        )


def cmd_backtest(args):
    from bot.backtest import run_backtest

    exchange = build_exchange()
    df = fetch_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.candles)
    result = run_backtest(df)
    print(f"نتائج الاختبار التاريخي لـ {args.symbol} ({args.timeframe}):")
    print(result.summary())


def cmd_trade(args):
    exchange, df, zones, signal = _prepare(args.symbol, args.timeframe, args.candles)
    price = float(df.iloc[-1]["close"])

    if not signal:
        print("لا توجد إشارة شراء/بيع حالياً. لم يُنفذ أي أمر.")
        return

    print(text_report(args.symbol, args.timeframe, zones, signal, price))

    live = args.live and args.confirm
    if args.live and not args.confirm:
        logger.error(
            "تم تمرير --live بدون --confirm. لأمان حسابك، التنفيذ الحقيقي يتطلب كلا العلمين معاً. "
            "سيتم التشغيل في وضع التجربة (dry-run) فقط."
        )

    balance_quote = args.balance
    if balance_quote is None:
        if live:
            print("يجب تمرير --balance (الرصيد المتاح بعملة التسعير) عند التنفيذ الحقيقي.")
            sys.exit(1)
        balance_quote = 1000.0  # رصيد افتراضي لوضع التجربة فقط
        print(f"(وضع تجربة: استخدام رصيد افتراضي {balance_quote} لحساب حجم الصفقة)")

    sizing = compute_position_size(balance_quote, signal)
    print(
        f"\nحجم الصفقة المحسوب: {sizing.quantity:.6f} | المخاطرة بالمال: {sizing.risk_amount:.2f} | "
        f"قيمة الصفقة: {sizing.position_value:.2f}"
    )

    if live:
        print("\n⚠️  تحذير: سيتم تنفيذ أمر حقيقي بأموال حقيقية الآن.")
    result = execute_signal(exchange, args.symbol, signal, sizing, live=live)
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="بوت تحليل السوق ومناطق البيع/الشراء")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", required=True, help="مثال: BTC/USDT")
    common.add_argument("--timeframe", default="4h", help="مثال: 15m, 1h, 4h, 1d")
    common.add_argument("--candles", type=int, default=400, help="عدد الشموع التاريخية المطلوبة")

    p_analyze = sub.add_parser("analyze", parents=[common], help="تحليل السوق وعرض المناطق والإشارة فقط")
    p_analyze.add_argument("--chart-out", default=None, help="مسار حفظ الرسم البياني (PNG)")
    p_analyze.set_defaults(func=cmd_analyze)

    p_backtest = sub.add_parser("backtest", parents=[common], help="اختبار الاستراتيجية على بيانات تاريخية")
    p_backtest.set_defaults(func=cmd_backtest)

    p_trade = sub.add_parser("trade", parents=[common], help="تحليل وتنفيذ صفقة (تجربة أو حقيقية)")
    p_trade.add_argument("--balance", type=float, default=None, help="الرصيد المتاح بعملة التسعير (مثل USDT)")
    p_trade.add_argument("--live", action="store_true", help="تفعيل التنفيذ الحقيقي (يتطلب --confirm أيضاً)")
    p_trade.add_argument("--confirm", action="store_true", help="تأكيد صريح بأنك تريد تنفيذ أوامر حقيقية بأموال حقيقية")
    p_trade.set_defaults(func=cmd_trade)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "trade" and args.live and args.confirm and not config.has_credentials():
        logger.error("طلبت التنفيذ الحقيقي لكن لا توجد مفاتيح API في .env. راجع .env.example.")
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
