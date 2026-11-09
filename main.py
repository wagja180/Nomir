"""نقطة الدخول الرئيسية لبوت تحليل السوق ومناطق البيع/الشراء.

أمثلة استخدام:
  python main.py analyze --symbol BTC/USDT --timeframe 4h
  python main.py backtest --symbol BTC/USDT --timeframe 4h --candles 1000
  python main.py trade --symbol BTC/USDT --timeframe 1h              # تجربة فقط (dry-run)
  python main.py trade --symbol BTC/USDT --timeframe 1h --live --confirm   # تنفيذ حقيقي
  python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15             # مراقبة مستمرة، تجربة
  python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15 --live --confirm  # مراقبة + تنفيذ حقيقي تلقائي
"""

import argparse
import datetime
import logging
import sys
import time

from bot.config import config
from bot.data_fetcher import build_exchange, fetch_ohlcv, fetch_quote_balance
from bot.executor import close_position, execute_signal
from bot.indicators import add_indicators
from bot.notify import notify
from bot.report import plot_chart, text_report
from bot.risk import compute_position_size
from bot.signals import generate_signal
from bot.state import OpenPosition, clear_open_position, load_open_position, save_open_position
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


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cmd_watch(args):
    """مراقبة مستمرة: يفحص السوق كل args.interval_minutes دقيقة، يفتح صفقة عند
    ظهور إشارة (إن لم تكن هناك صفقة مفتوحة بالفعل)، ويراقب وقف الخسارة/الهدف
    لإغلاقها. يحفظ حالة الصفقة المفتوحة في ملف JSON حتى لا يفتح صفقات مكررة
    بين دورة وأخرى."""

    exchange = build_exchange()
    live = args.live and args.confirm
    if args.live and not args.confirm:
        logger.error(
            "تم تمرير --live بدون --confirm. لأمان حسابك، التنفيذ الحقيقي يتطلب كلا العلمين معاً. "
            "سيتم التشغيل في وضع التجربة (dry-run) فقط."
        )

    state_path = args.state_file or f"state_{args.symbol.replace('/', '_')}.json"

    print(f"بدء المراقبة المستمرة لـ {args.symbol} ({args.timeframe}) كل {args.interval_minutes} دقيقة.")
    print(f"ملف تتبع الحالة: {state_path}")
    if live:
        print("⚠️  وضع التنفيذ الحقيقي مفعّل: سيتم فتح وإغلاق صفقات حقيقية بأموال حقيقية تلقائياً بدون تدخلك.")
    else:
        print("(وضع تجربة dry-run: لن يُنفذ أي أمر حقيقي، فقط محاكاة ومراقبة لإظهار السلوك الكامل.)")
    print("اضغط Ctrl+C لإيقاف المراقبة في أي وقت.\n")

    iterations = 0
    try:
        while True:
            iterations += 1
            ts = _now()
            try:
                df = fetch_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.candles)
                df = add_indicators(df)
                last = df.iloc[-1]
                price = float(last["close"])

                position = load_open_position(state_path)

                if position:
                    hit_stop = (position.side == "buy" and float(last["low"]) <= position.stop_loss) or (
                        position.side == "sell" and float(last["high"]) >= position.stop_loss
                    )
                    hit_target = (position.side == "buy" and float(last["high"]) >= position.take_profit) or (
                        position.side == "sell" and float(last["low"]) <= position.take_profit
                    )
                    if hit_stop or hit_target:
                        reason = "وقف الخسارة" if hit_stop else "الهدف"
                        result = close_position(exchange, args.symbol, position, live=live)
                        print(f"[{ts}] إغلاق الصفقة ({position.side}) عند {reason}. {result}")
                        notify(f"إغلاق صفقة {position.side} — {args.symbol}", f"{reason} عند {price:.6f}")
                        clear_open_position(state_path)
                    else:
                        print(f"[{ts}] صفقة مفتوحة ({position.side}) منذ {position.opened_at}، السعر الحالي={price:.6f}، ننتظر الوقف/الهدف.")
                else:
                    zones = detect_zones(df)
                    signal = generate_signal(df, zones)
                    if signal:
                        if live:
                            balance_quote = fetch_quote_balance(exchange, args.symbol)
                        else:
                            balance_quote = args.balance or 1000.0
                        sizing = compute_position_size(balance_quote, signal)
                        result = execute_signal(exchange, args.symbol, signal, sizing, live=live)
                        print(f"[{ts}] إشارة {signal.side} جديدة! {result}")
                        notify(
                            f"إشارة {signal.side} جديدة — {args.symbol}",
                            f"سعر الدخول {signal.price:.6f} | وقف {signal.stop_loss:.6f} | هدف {signal.take_profit:.6f}",
                        )
                        if sizing.quantity > 0:
                            save_open_position(
                                state_path,
                                OpenPosition(
                                    symbol=args.symbol,
                                    side=signal.side,
                                    entry_price=signal.price,
                                    stop_loss=signal.stop_loss,
                                    take_profit=signal.take_profit,
                                    quantity=sizing.quantity,
                                    opened_at=ts,
                                ),
                            )
                    else:
                        print(f"[{ts}] لا توجد إشارة الآن. السعر={price:.6f}")
            except Exception as exc:  # لا نوقف المراقبة المستمرة بسبب خطأ عابر (شبكة، إلخ)
                logger.error("[%s] خطأ في دورة المراقبة: %s", ts, exc)

            if args.max_iterations and iterations >= args.max_iterations:
                break
            time.sleep(args.interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nتم إيقاف المراقبة بواسطتك.")


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

    p_watch = sub.add_parser("watch", parents=[common], help="مراقبة مستمرة مع تتبع حالة الصفقة (تجربة أو تنفيذ تلقائي حقيقي)")
    p_watch.add_argument("--interval-minutes", type=float, default=15, help="الفاصل الزمني بين كل فحص (بالدقائق)")
    p_watch.add_argument("--balance", type=float, default=None, help="رصيد وضع التجربة الافتراضي (يُتجاهل في live، حيث يُجلب الرصيد الحقيقي من المنصة)")
    p_watch.add_argument("--state-file", default=None, help="مسار ملف تتبع حالة الصفقة (افتراضياً state_<الرمز>.json)")
    p_watch.add_argument("--max-iterations", type=int, default=None, help="إيقاف تلقائي بعد هذا العدد من الدورات (للاختبار)")
    p_watch.add_argument("--live", action="store_true", help="تفعيل التنفيذ الحقيقي (يتطلب --confirm أيضاً)")
    p_watch.add_argument("--confirm", action="store_true", help="تأكيد صريح بأنك تريد تنفيذ أوامر حقيقية بأموال حقيقية تلقائياً")
    p_watch.set_defaults(func=cmd_watch)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command in ("trade", "watch") and args.live and args.confirm and not config.has_credentials():
        logger.error("طلبت التنفيذ الحقيقي لكن لا توجد مفاتيح API في .env. راجع .env.example.")
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
