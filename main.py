"""نقطة الدخول الرئيسية لبوت تحليل السوق ومناطق البيع/الشراء.

أمثلة استخدام:
  python main.py analyze --symbol BTC/USDT --timeframe 4h
  python main.py backtest --symbol BTC/USDT --timeframe 4h --candles 1000
  python main.py trade --symbol BTC/USDT --timeframe 1h              # تجربة فقط (dry-run)
  python main.py trade --symbol BTC/USDT --timeframe 1h --live --confirm   # تنفيذ حقيقي
  python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15             # مراقبة مستمرة، تجربة
  python main.py watch --symbol BTC/USDT --timeframe 1h --interval-minutes 15 --live --confirm  # مراقبة + تنفيذ حقيقي تلقائي
  python main.py watch --symbol "BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT,XRP/USDT" --timeframe 1h --live --confirm  # عدة عملات معاً
"""

import argparse
import datetime
import logging
import sys
import time

import pandas as pd

from bot.config import config
from bot.data_fetcher import build_exchange, fetch_base_balance, fetch_ohlcv, fetch_quote_balance
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

    # التداول الفوري (Spot) لا يسمح بالبيع على المكشوف: تحقق من وجود رصيد كافٍ
    # من عملة الأساس قبل إرسال أمر بيع حقيقي، كما يفعل أمر watch تماماً.
    if live and signal.side == "sell":
        base_balance = fetch_base_balance(exchange, args.symbol)
        if base_balance < sizing.quantity:
            base = args.symbol.split("/")[0]
            print(
                f"إشارة بيع لكن لا يوجد رصيد كافٍ من {base} "
                f"({base_balance:.8f} متاح، {sizing.quantity:.8f} مطلوب). لم يُنفذ أي أمر."
            )
            return

    if live:
        print("\n⚠️  تحذير: سيتم تنفيذ أمر حقيقي بأموال حقيقية الآن.")
    result = execute_signal(exchange, args.symbol, signal, sizing, live=live)
    print(result)

    # هذا أمر تنفيذ لمرة واحدة (trade) لا يراقب الصفقة بعد فتحها، بخلاف watch.
    # إن نُفّذ أمر حقيقي فعلاً، احفظ حالته بنفس آلية watch حتى يمكن لاحقاً
    # تشغيل `watch` على نفس الرمز فيلتقط هذه الصفقة ويحميها (خاصة لو فشل
    # وضع OCO ولم تبقَ أي حماية على المنصة إطلاقاً).
    if live and result.order is not None:
        state_path = f"state_{args.symbol.replace('/', '_')}.json"
        actual_quantity = result.filled_quantity if result.filled_quantity else sizing.quantity
        save_open_position(
            state_path,
            OpenPosition(
                symbol=args.symbol,
                side=signal.side,
                entry_price=signal.price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                quantity=actual_quantity,
                opened_at=_now(),
                live=True,
                protective_order_id=result.protective_order_id,
                protective_order_list_id=result.protective_order_list_id,
            ),
        )
        if not result.protective_order_id:
            print(
                f"\n⚠️  تحذير مهم: لم يُوضع أمر حماية (وقف/هدف) على المنصة لهذه الصفقة. "
                f"حُفظت حالتها في {state_path}، لكنها بلا أي حماية فعلية حتى تُشغّل:\n"
                f"  python main.py watch --symbol {args.symbol} --timeframe {args.timeframe} --live --confirm"
            )
        else:
            print(f"\nتم حفظ حالة الصفقة في {state_path} — شغّل watch على نفس الرمز لمتابعتها تلقائياً.")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _state_path_for(symbol: str, override: str | None) -> str:
    if override:
        return override
    return f"state_{symbol.replace('/', '_')}.json"


def cmd_watch(args):
    """مراقبة مستمرة لرمز واحد أو عدة رموز معاً (مفصولة بفاصلة في --symbol).
    يفحص كل رمز كل args.interval_minutes دقيقة، يفتح صفقة عند ظهور إشارة (إن
    لم تكن هناك صفقة مفتوحة له ولم يُبلَغ الحد الأقصى الإجمالي للصفقات
    المفتوحة MAX_OPEN_POSITIONS)، ويراقب وقف الخسارة/الهدف لإغلاقها. يحفظ حالة
    كل صفقة في ملف JSON منفصل لكل رمز حتى لا تُفتح صفقات مكررة بين دورة وأخرى،
    ولا يتوزع رأس المال المشترك (عملة تسعير واحدة عادة) على أكثر مما يتحمّل."""

    symbols = [s.strip() for s in args.symbol.split(",") if s.strip()]
    exchange = build_exchange()
    live = args.live and args.confirm
    if args.live and not args.confirm:
        logger.error(
            "تم تمرير --live بدون --confirm. لأمان حسابك، التنفيذ الحقيقي يتطلب كلا العلمين معاً. "
            "سيتم التشغيل في وضع التجربة (dry-run) فقط."
        )

    state_file_override = args.state_file
    if state_file_override and len(symbols) > 1:
        logger.error("خيار --state-file غير مدعوم مع أكثر من رمز في نفس الوقت؛ سيُستخدم ملف تلقائي منفصل لكل رمز.")
        state_file_override = None

    print(f"بدء المراقبة المستمرة لـ {', '.join(symbols)} ({args.timeframe}) كل {args.interval_minutes} دقيقة.")
    print(f"الحد الأقصى للصفقات المفتوحة في آن واحد عبر كل الرموز: {config.max_open_positions}")
    if live:
        print("⚠️  وضع التنفيذ الحقيقي مفعّل: سيتم فتح وإغلاق صفقات حقيقية بأموال حقيقية تلقائياً بدون تدخلك.")
    else:
        print("(وضع تجربة dry-run: لن يُنفذ أي أمر حقيقي، فقط محاكاة ومراقبة لإظهار السلوك الكامل.)")
    print("اضغط Ctrl+C لإيقاف المراقبة في أي وقت.\n")

    iterations = 0
    try:
        while True:
            iterations += 1

            open_count = sum(
                1 for s in symbols if load_open_position(_state_path_for(s, state_file_override)) is not None
            )

            for symbol in symbols:
                ts = _now()
                state_path = _state_path_for(symbol, state_file_override)
                tag = f"[{symbol}]" if len(symbols) > 1 else ""
                try:
                    df = fetch_ohlcv(exchange, symbol, timeframe=args.timeframe, limit=args.candles)
                    df = add_indicators(df)
                    last = df.iloc[-1]
                    price = float(last["close"])

                    position = load_open_position(state_path)

                    # صفقة محاكاة (dry-run) محفوظة سابقاً يجب ألا تُغلَق أبداً بأمر
                    # حقيقي إن شُغّل البوت لاحقاً بوضع live (والعكس: صفقة حقيقية لا
                    # يجوز التعامل معها إلا بأوامر حقيقية). عدم التطابق يعني أن ملف
                    # الحالة من جلسة بوضع مختلف؛ نتعامل معها دائماً كمحاكاة فقط.
                    position_is_real = bool(position and position.live)
                    close_live = live and position_is_real

                    if position:
                        if live != position_is_real:
                            print(
                                f"[{ts}] {tag} تحذير: صفقة محفوظة بوضع "
                                f"{'حقيقي' if position_is_real else 'تجربة'} أثناء تشغيل البوت الآن بوضع "
                                f"{'حقيقي' if live else 'تجربة'} — ستُعامَل كمحاكاة فقط لتفادي أمر حقيقي خاطئ."
                            )
                        # افحص كل الشموع منذ فتح الصفقة، لا الشمعة الأخيرة فقط —
                        # لو توقف البوت أو تأخر لأي سبب (انقطاع شبكة/خادم) أكثر
                        # من فترة شمعة واحدة، قد يكون الوقف أو الهدف قد لامسه
                        # السعر في شمعة سابقة لم تعد هي الأخيرة في البيانات
                        # المجلوبة الآن، فيُفوَّت تماماً لو اكتفينا بالأخيرة فقط.
                        try:
                            opened_at_ts = pd.Timestamp(position.opened_at)
                            window = df[df.index >= opened_at_ts]
                            if window.empty:
                                window = df.iloc[[-1]]
                        except Exception:
                            window = df.iloc[[-1]]
                        hit_stop = (
                            (position.side == "buy" and (window["low"] <= position.stop_loss).any())
                            or (position.side == "sell" and (window["high"] >= position.stop_loss).any())
                        )
                        hit_target = (
                            (position.side == "buy" and (window["high"] >= position.take_profit).any())
                            or (position.side == "sell" and (window["low"] <= position.take_profit).any())
                        )
                        if hit_stop or hit_target:
                            reason = "وقف الخسارة" if hit_stop else "الهدف"
                            result = close_position(exchange, symbol, position, live=close_live)
                            print(f"[{ts}] {tag} إغلاق الصفقة ({position.side}) عند {reason}. {result}")
                            notify(f"إغلاق صفقة {position.side} — {symbol}", f"{reason} عند {price:.6f}")
                            # لا تُمسح حالة الصفقة إلا إذا أُغلقت فعلاً:
                            #   - محاكاة كاملة (الصفقة نفسها غير حقيقية أصلاً): آمن.
                            #   - أمر بيع حقيقي نُفّذ فعلاً (result.order موجود).
                            #   - تأكدنا أنها مُغلقة مسبقاً فعلاً على المنصة.
                            # أما إن كانت الصفقة حقيقية (position_is_real) لكن
                            # البوت يعمل الآن بوضع تجربة (close_live=False ومن ثم
                            # result.dry_run=True)، فهذا لا يعني أنها أُغلقت على
                            # المنصة فعلاً — يجب أن تبقى مُتتبَّعة حتى تُغلق بجلسة
                            # حقيقية فعلاً، وإلا فُقد تتبّعها دون أي إغلاق حقيقي.
                            safe_to_clear = (
                                (result.dry_run and not position_is_real)
                                or result.order is not None
                                or result.already_closed
                            )
                            if safe_to_clear:
                                clear_open_position(state_path)
                                open_count -= 1
                            else:
                                print(f"[{ts}] {tag} الصفقة لا تزال مفتوحة فعلياً، سيُعاد المحاولة في الدورة القادمة.")
                        else:
                            print(f"[{ts}] {tag} صفقة مفتوحة ({position.side}) منذ {position.opened_at}، السعر الحالي={price:.6f}، ننتظر الوقف/الهدف.")
                    elif open_count >= config.max_open_positions:
                        print(f"[{ts}] {tag} تم بلوغ الحد الأقصى للصفقات المفتوحة ({config.max_open_positions})، تم تجاهل البحث عن إشارة جديدة.")
                    else:
                        zones = detect_zones(df)
                        signal = generate_signal(df, zones)
                        if signal:
                            if live:
                                balance_quote = fetch_quote_balance(exchange, symbol)
                            else:
                                balance_quote = args.balance or 1000.0
                            sizing = compute_position_size(balance_quote, signal)

                            # التداول الفوري (Spot) لا يسمح بالبيع على المكشوف: تجاهل
                            # إشارات البيع بأمان إن لم نملك كمية كافية من عملة الأساس،
                            # بدل تكرار محاولة فاشلة كل دورة بخطأ "رصيد غير كافٍ".
                            skip_sell = False
                            if live and signal.side == "sell":
                                base_balance = fetch_base_balance(exchange, symbol)
                                if base_balance < sizing.quantity:
                                    base = symbol.split("/")[0]
                                    print(
                                        f"[{ts}] {tag} إشارة بيع لكن لا يوجد رصيد كافٍ من {base} "
                                        f"({base_balance:.8f} متاح، {sizing.quantity:.8f} مطلوب). تم تجاهلها."
                                    )
                                    skip_sell = True

                            if not skip_sell:
                                result = execute_signal(exchange, symbol, signal, sizing, live=live)
                                print(f"[{ts}] {tag} إشارة {signal.side} جديدة! {result}")
                                notify(
                                    f"إشارة {signal.side} جديدة — {symbol}",
                                    f"سعر الدخول {signal.price:.6f} | وقف {signal.stop_loss:.6f} | هدف {signal.take_profit:.6f}",
                                )
                                if sizing.quantity > 0:
                                    # عند التنفيذ الحقيقي، سجّل الكمية الفعلية التي
                                    # امتلكناها بعد التنفيذ (بعد خصم الرسوم وتقريب
                                    # المنصة)، لا الكمية المطلوبة أصلاً، تفادياً
                                    # لخطأ "رصيد غير كافٍ" لاحقاً عند إغلاق الصفقة.
                                    actual_quantity = (
                                        result.filled_quantity
                                        if live and result.filled_quantity
                                        else sizing.quantity
                                    )
                                    save_open_position(
                                        state_path,
                                        OpenPosition(
                                            symbol=symbol,
                                            side=signal.side,
                                            entry_price=signal.price,
                                            stop_loss=signal.stop_loss,
                                            take_profit=signal.take_profit,
                                            quantity=actual_quantity,
                                            opened_at=ts,
                                            live=live,
                                            protective_order_id=result.protective_order_id if live else None,
                                            protective_order_list_id=result.protective_order_list_id if live else None,
                                        ),
                                    )
                                    open_count += 1
                        else:
                            print(f"[{ts}] {tag} لا توجد إشارة الآن. السعر={price:.6f}")
                except Exception as exc:  # لا نوقف المراقبة المستمرة بسبب خطأ عابر (شبكة، إلخ)
                    logger.error("[%s] %s خطأ في دورة المراقبة: %s", ts, tag, exc)

            if args.max_iterations and iterations >= args.max_iterations:
                break
            time.sleep(args.interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nتم إيقاف المراقبة بواسطتك.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="بوت تحليل السوق ومناطق البيع/الشراء")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--symbol", required=True, help="مثال: BTC/USDT (أو عدة رموز مفصولة بفاصلة لأمر watch: \"BTC/USDT,ETH/USDT\")")
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
