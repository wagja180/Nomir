"""تنفيذ الصفقات الحقيقية عبر المنصة (ccxt)، مع وضع تجربة (dry-run) افتراضي.

تحذير: هذا الملف قادر على تنفيذ أوامر شراء/بيع حقيقية بأموال حقيقية عند تفعيل
وضع live. التشغيل الفعلي يتطلب:
  1. مفاتيح API صحيحة في .env (EXCHANGE_API_KEY / EXCHANGE_API_SECRET).
  2. تمرير live=True صراحةً عند استدعاء execute_signal.
  3. تأكيد المستخدم عبر علم --live --confirm في سطر الأوامر (main.py).
بدون كل هذه الشروط، لا يتم إرسال أي أمر حقيقي؛ يتم فقط تسجيل ما كان سيحدث.
"""

import logging

import ccxt

from bot.config import config
from bot.risk import PositionSizing
from bot.signals import Signal
from bot.state import OpenPosition

logger = logging.getLogger("bot.executor")


class ExecutionResult:
    def __init__(
        self,
        dry_run: bool,
        order: dict | None,
        message: str,
        already_closed: bool = False,
        filled_quantity: float | None = None,
        protective_order_id: str | None = None,
        protective_order_list_id: str | None = None,
    ):
        self.dry_run = dry_run
        self.order = order
        self.message = message
        # True فقط عند اكتشاف close_position أن الصفقة مُغلقة مسبقاً على
        # المنصة (مثلاً نفّذ أمر OCO الوقف/الهدف قبل أن تصل حلقة المراقبة
        # لنفس القرار)، فلا يوجد رصيد كافٍ لإغلاقها يدوياً مجدداً.
        self.already_closed = already_closed
        # الكمية الفعلية المملوكة بعد التنفيذ (بعد خصم رسوم التداول المدفوعة
        # بعملة الأساس، وبعد تقريب المنصة للكمية المطلوبة). قد تقل قليلاً عن
        # sizing.quantity الأصلية؛ يجب استخدامها لا الكمية المطلوبة عند حفظ
        # حالة الصفقة، تفادياً لخطأ "رصيد غير كافٍ" لاحقاً عند الإغلاق.
        self.filled_quantity = filled_quantity
        # معرّف أمر الحماية (OCO) الذي وُضع فعلاً لهذه الصفقة تحديداً، إن نجح
        # وضعه. يُحفظ في حالة الصفقة لاستخدامه لاحقاً عند الإغلاق بدل إلغاء كل
        # الأوامر المعلّقة على الرمز (التي قد تخص المستخدم يدوياً لا البوت).
        self.protective_order_id = protective_order_id
        self.protective_order_list_id = protective_order_list_id

    def __repr__(self) -> str:
        mode = "تجربة (dry-run)" if self.dry_run else "حقيقي (live)"
        return f"<ExecutionResult {mode}: {self.message}>"


def execute_signal(
    exchange: ccxt.Exchange,
    symbol: str,
    signal: Signal,
    sizing: PositionSizing,
    live: bool = False,
) -> ExecutionResult:
    """ينفذ أمر سوق (market order) بناءً على الإشارة، أو يحاكيه فقط إذا live=False."""

    if sizing.quantity <= 0:
        return ExecutionResult(dry_run=not live, order=None, message="حجم الصفقة صفر، لم يُنفذ أي أمر.")

    if not live:
        msg = (
            f"[تجربة] أمر {signal.side} لـ {symbol}: الكمية={sizing.quantity:.6f}, "
            f"سعر الدخول≈{signal.price:.4f}, وقف الخسارة={signal.stop_loss:.4f}, "
            f"الهدف={signal.take_profit:.4f}"
        )
        logger.info(msg)
        return ExecutionResult(dry_run=True, order=None, message=msg)

    if not config.has_credentials():
        raise RuntimeError(
            "طلب تنفيذ حقيقي (live) بدون مفاتيح API. أضف EXCHANGE_API_KEY و "
            "EXCHANGE_API_SECRET في ملف .env أولاً."
        )

    side = "buy" if signal.side == "buy" else "sell"
    order = exchange.create_order(symbol, type="market", side=side, amount=sizing.quantity)
    logger.warning("تم تنفيذ أمر حقيقي: %s", order)

    filled_quantity = _actual_filled_base_quantity(order, symbol, side, fallback=sizing.quantity)

    opposite_side = "sell" if side == "buy" else "buy"
    protective_order_id, protective_order_list_id = _place_protective_oco(
        exchange, symbol, opposite_side, filled_quantity, signal.stop_loss, signal.take_profit
    )

    return ExecutionResult(
        dry_run=False,
        order=order,
        message=f"تم تنفيذ أمر {side} حقيقي بكمية {filled_quantity:.6f}",
        filled_quantity=filled_quantity,
        protective_order_id=protective_order_id,
        protective_order_list_id=protective_order_list_id,
    )


def _actual_filled_base_quantity(order: dict, symbol: str, side: str, fallback: float) -> float:
    """يحسب الكمية الفعلية المملوكة من عملة الأساس بعد التنفيذ، بخصم أي رسوم
    مدفوعة بنفس العملة. المنصة تُقرّب الكمية المطلوبة لأقرب دقة مسموحة، وقد
    تُخصم الرسوم من نفس عملة الأساس عند الشراء — فالكمية المطلوبة أصلاً
    (sizing.quantity) قد تكون أكبر قليلاً من المملوك فعلياً، ما يسبب لاحقاً
    خطأ "رصيد غير كافٍ" عند محاولة إغلاق الصفقة بنفس الكمية المسجّلة."""
    if side != "buy":
        return fallback
    try:
        base_asset = symbol.split("/")[0]
        filled = float(order.get("filled") or order.get("amount") or fallback)
        fees = order.get("fees") or ([order["fee"]] if order.get("fee") else [])
        base_fee = sum(float(fee.get("cost") or 0.0) for fee in fees if fee and fee.get("currency") == base_asset)
        net = filled - base_fee
        return net if net > 0 else fallback
    except Exception:
        return fallback


def _place_protective_oco(
    exchange: ccxt.Exchange,
    symbol: str,
    opposite_side: str,
    quantity: float,
    stop_loss: float,
    take_profit: float,
) -> tuple[str | None, str | None]:
    """يحاول وضع أمر OCO واحد (وقف خسارة + جني ربح مرتبطان بنفس الكمية) على
    المنصة مباشرة بعد الدخول. نوع "stop_market" المنفصل غير مقبول على أسواق
    Binance Spot (يُرفض بخطأ "not a valid order type"), ووضع أمرين منفصلين
    (وقف وهدف) لنفس الكمية دون ربطهما بـ OCO قد يتطلب حجز الكمية مرتين.

    إن تعذّر وضع OCO (منصة لا تدعمه لهذا الزوج تحديداً — يحدث فعلياً مع بعض
    أزواج Binance، أو خطأ آخر)، تبقى حماية الصفقة معتمدة بالكامل على حلقة
    `watch` في هذا البوت التي تراقب السعر وتُغلق الصفقة يدوياً عند الوصول
    للوقف أو الهدف — لذا يجب أن تبقى هذه العملية تعمل باستمرار.

    يُرجع (order_id, order_list_id) عند النجاح لحفظهما في حالة الصفقة، حتى
    يُلغى هذا الأمر بالذات فقط عند الإغلاق لاحقاً، لا كل الأوامر المعلّقة على
    الرمز (التي قد يضعها المستخدم يدوياً لأغراض أخرى)."""

    stop_limit_price = stop_loss * (0.995 if opposite_side == "sell" else 1.005)
    try:
        oco_order = exchange.create_order(
            symbol,
            "oco",
            opposite_side,
            quantity,
            take_profit,
            params={
                "stopPrice": stop_loss,
                "stopLimitPrice": stop_limit_price,
                "stopLimitTimeInForce": "GTC",
            },
        )
        order_id = oco_order.get("id")
        order_list_id = (oco_order.get("info") or {}).get("orderListId")
        return (str(order_id) if order_id else None, str(order_list_id) if order_list_id else None)
    except Exception as exc:
        logger.warning("تعذر وضع أمر OCO (وقف+هدف مرتبطان) على المنصة: %s", exc)

    logger.warning(
        "لا توجد أوامر وقف/هدف مُعلّقة على المنصة لهذه الصفقة. إغلاقها يعتمد "
        "بالكامل على استمرار عمل حلقة watch لمراقبتها يدوياً."
    )
    return (None, None)


def close_position(
    exchange: ccxt.Exchange,
    symbol: str,
    position: OpenPosition,
    live: bool = False,
) -> ExecutionResult:
    """يغلق صفقة مفتوحة بأمر سوق معاكس، أو يحاكي ذلك فقط إذا live=False.

    يحاول أولاً إلغاء أي أوامر وقف/هدف معلّقة على المنصة لتفادي تنفيذ مزدوج
    (أمرنا اليدوي + أمر الوقف/الهدف الذي قد يُنفَّذ في نفس اللحظة تقريباً)."""

    opposite_side = "sell" if position.side == "buy" else "buy"

    if not live:
        msg = f"[تجربة] إغلاق صفقة {position.side} لـ {symbol} بكمية {position.quantity:.6f}"
        logger.info(msg)
        return ExecutionResult(dry_run=True, order=None, message=msg)

    _cancel_position_protective_order(exchange, symbol, position.protective_order_id, position.protective_order_list_id)

    try:
        order = exchange.create_order(symbol, type="market", side=opposite_side, amount=position.quantity)
    except ccxt.InsufficientFunds as exc:
        # رصيد غير كافٍ للإغلاق له سببان مختلفان تماماً، ويجب التمييز بينهما
        # بدقة قبل التخلي عن تتبّع الصفقة:
        #   1) أمر الحماية (OCO) الخاص بهذه الصفقة تحديداً لا يزال معلّقاً
        #      (فشل إلغاؤه أعلاه) → العملة لا تزال محجوزة به، والصفقة لم
        #      تُغلق فعلياً. يجب عدم مسح الحالة.
        #   2) لا يوجد أمر حماية معلّق خاص بنا (أُلغي بنجاح، أو لم يُوضع
        #      أصلاً لأن OCO غير مدعوم لهذا الزوج) → السبب الحقيقي غير معروف
        #      بعد؛ تحقّق من الرصيد الفعلي قبل أي استنتاج.
        if _is_order_still_open(exchange, symbol, position.protective_order_id):
            msg = (
                f"تعذر إغلاق الصفقة: أمر الحماية (OCO) الخاص بها لا يزال معلّقاً "
                f"ولم يُمكن إلغاؤه. الصفقة لا تزال مفتوحة فعلياً، سنعيد المحاولة لاحقاً: {exc}"
            )
            logger.error(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=False)

        # لا يوجد أمر حماية خاص بنا لا يزال معلّقاً، لكن هذا وحده لا يكفي
        # لاستنتاج أن الصفقة أُغلقت فعلاً عبر OCO — فقد لا يكون OCO مدعوماً
        # أصلاً لهذا الزوج (يحدث فعلياً مع بعض أزواج Binance)، وعندها "لا
        # يوجد أمر معلّق" صحيح منذ البداية دون أي علاقة بإغلاق حقيقي. تحقّق
        # من الرصيد الفعلي المتبقي من عملة الأساس قبل اتخاذ أي قرار.
        base_asset = symbol.split("/")[0]
        try:
            balance = exchange.fetch_balance()
            available = float((balance.get(base_asset) or {}).get("free") or 0.0)
        except Exception as balance_exc:
            msg = (
                f"تعذر إغلاق الصفقة وتعذر أيضاً التحقق من الرصيد المتبقي من {base_asset} "
                f"للتأكد إن كانت مُغلقة فعلاً. الصفقة تبقى مُتتبَّعة احتياطاً: {balance_exc}"
            )
            logger.error(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=False)

        if available <= 0:
            msg = f"الصفقة مُغلقة على المنصة على الأرجح (لا يوجد رصيد متبقٍ من {base_asset}): {exc}"
            logger.warning(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=True)

        # لا يزال هناك رصيد فعلي (أقل عادة من الكمية المسجّلة بسبب رسوم أو
        # تقريب عند فتح الصفقة) — أغلق الصفقة فعلياً بالكمية الفعلية المتاحة
        # بدل التخلي عن تتبّعها دون سبب حقيقي.
        try:
            retry_order = exchange.create_order(symbol, type="market", side=opposite_side, amount=available)
        except ccxt.InvalidOrder as dust_exc:
            # هذا الخطأ تحديداً (وليس أي استثناء آخر) يعني أن الكمية المتبقية
            # أقل من الحد الأدنى المسموح بالتداول (غبار) — آمن اعتبارها
            # مُغلقة فعلياً من الناحية العملية، إذ لا يمكن بيعها أصلاً.
            msg = (
                f"لا يزال هناك رصيد فعلي {available:.8f} {base_asset} لكنه كمية غبار "
                f"أقل من الحد الأدنى المسموح بالبيع. سنعتبرها مُغلقة فعلياً: {dust_exc}"
            )
            logger.warning(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=True)
        except Exception as retry_exc:
            # أي خطأ آخر (شبكة، تقييد مؤقت، إلخ) قد يكون عابراً — لا نفترض
            # أبداً أن الصفقة أُغلقت لمجرد فشل محاولة إعادة البيع؛ هذا بالضبط
            # ما يسبب فقدان تتبّع صفقة لا تزال مفتوحة فعلياً بأموال حقيقية.
            msg = (
                f"لا يزال هناك رصيد فعلي {available:.8f} {base_asset} لكن تعذر بيعه الآن "
                f"لسبب آخر غير واضح أنه نهائي. الصفقة تبقى مُتتبَّعة لإعادة المحاولة لاحقاً: {retry_exc}"
            )
            logger.error(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=False)

        logger.warning(
            "تم إغلاق الصفقة الحقيقية بالكمية الفعلية المتاحة (%.8f بدل %.8f المسجّلة بسبب فرق رسوم/تقريب): %s",
            available, position.quantity, retry_order,
        )
        return ExecutionResult(
            dry_run=False,
            order=retry_order,
            message=(
                f"تم إغلاق الصفقة بأمر {opposite_side} حقيقي بكمية فعلية {available:.8f} "
                f"{base_asset} (بدل {position.quantity:.8f} المسجّلة)"
            ),
        )

    logger.warning("تم إغلاق الصفقة الحقيقية: %s", order)
    return ExecutionResult(dry_run=False, order=order, message=f"تم إغلاق الصفقة بأمر {opposite_side} حقيقي بكمية {position.quantity:.6f}")


def _cancel_position_protective_order(
    exchange: ccxt.Exchange, symbol: str, order_id: str | None, order_list_id: str | None
) -> None:
    """يلغي أمر الحماية (OCO) الخاص بهذه الصفقة تحديداً فقط، إن كان معروفاً،
    دون المساس بأي أوامر أخرى قد يضعها المستخدم يدوياً على نفس الرمز لأغراض
    غير متعلقة بالبوت."""
    if not order_id:
        return
    try:
        if order_list_id:
            exchange.cancel_order(order_id, symbol, params={"orderListId": order_list_id})
        else:
            exchange.cancel_order(order_id, symbol)
    except Exception as exc:
        logger.warning("تعذر إلغاء أمر الحماية (OCO) الخاص بالصفقة %s: %s", order_id, exc)


def _is_order_still_open(exchange: ccxt.Exchange, symbol: str, order_id: str | None) -> bool:
    """هل أمر الحماية الخاص بنا (إن وُجد) لا يزال معلّقاً فعلاً على المنصة؟
    None إن لم يُوضع أصلاً أي أمر حماية من قِبلنا (OCO فشل أو غير مدعوم)، وفي
    هذه الحالة لا شيء من جهتنا يحجز الرصيد."""
    if not order_id:
        return False
    try:
        open_orders = exchange.fetch_open_orders(symbol)
    except Exception:
        return True  # تعذّر التأكد؛ نتعامل بحذر كأنه لا يزال معلّقاً
    return any(str(o.get("id")) == str(order_id) for o in open_orders)
