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
    _place_protective_oco(exchange, symbol, opposite_side, filled_quantity, signal.stop_loss, signal.take_profit)

    return ExecutionResult(
        dry_run=False,
        order=order,
        message=f"تم تنفيذ أمر {side} حقيقي بكمية {filled_quantity:.6f}",
        filled_quantity=filled_quantity,
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
) -> None:
    """يحاول وضع أمر OCO واحد (وقف خسارة + جني ربح مرتبطان بنفس الكمية) على
    المنصة مباشرة بعد الدخول. نوع "stop_market" المنفصل غير مقبول على أسواق
    Binance Spot (يُرفض بخطأ "not a valid order type"), ووضع أمرين منفصلين
    (وقف وهدف) لنفس الكمية دون ربطهما بـ OCO قد يتطلب حجز الكمية مرتين.

    إن تعذّر وضع OCO (منصة لا تدعمه، أو خطأ آخر)، تبقى حماية الصفقة معتمدة
    بالكامل على حلقة `watch` في هذا البوت التي تراقب السعر وتُغلق الصفقة يدوياً
    عند الوصول للوقف أو الهدف — لذا يجب أن تبقى هذه العملية تعمل باستمرار."""

    stop_limit_price = stop_loss * (0.995 if opposite_side == "sell" else 1.005)
    try:
        exchange.create_order(
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
        return
    except Exception as exc:
        logger.warning("تعذر وضع أمر OCO (وقف+هدف مرتبطان) على المنصة: %s", exc)

    logger.warning(
        "لا توجد أوامر وقف/هدف مُعلّقة على المنصة لهذه الصفقة. إغلاقها يعتمد "
        "بالكامل على استمرار عمل حلقة watch لمراقبتها يدوياً."
    )


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

    _cancel_open_orders(exchange, symbol)

    try:
        order = exchange.create_order(symbol, type="market", side=opposite_side, amount=position.quantity)
    except ccxt.InsufficientFunds as exc:
        # رصيد غير كافٍ للإغلاق له سببان مختلفان تماماً، ويجب التمييز بينهما
        # بدقة قبل التخلي عن تتبّع الصفقة:
        #   1) لا توجد أوامر معلّقة على المنصة الآن → الأرجح أن أمر OCO نفّذ
        #      الصفقة فعلاً قبل وصولنا لنفس القرار. الصفقة مُغلقة بالفعل.
        #   2) لا تزال أوامر معلّقة موجودة (فشل إلغاؤها أعلاه) → العملة لا
        #      تزال محجوزة بها، والصفقة لم تُغلق فعلياً. يجب عدم مسح الحالة.
        try:
            remaining = exchange.fetch_open_orders(symbol)
        except Exception:
            remaining = None  # تعذّر التأكد؛ نتعامل معه بحذر كأنه لا يزال مفتوحاً

        if remaining:
            msg = (
                f"تعذر إغلاق الصفقة: لا تزال {len(remaining)} أوامر معلّقة تحجز الرصيد "
                f"ولم يُمكن إلغاؤها. الصفقة لا تزال مفتوحة فعلياً، سنعيد المحاولة لاحقاً: {exc}"
            )
            logger.error(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=False)

        # لا توجد أوامر معلّقة الآن، لكن هذا وحده لا يكفي لاستنتاج أن الصفقة
        # أُغلقت فعلاً عبر OCO — فقد لا يكون OCO مدعوماً أصلاً لهذا الزوج (يحدث
        # فعلياً مع بعض أزواج Binance)، وعندها "لا توجد أوامر معلّقة" صحيحة منذ
        # البداية دون أي علاقة بإغلاق حقيقي. تحقّق من الرصيد الفعلي المتبقي من
        # عملة الأساس قبل اتخاذ أي قرار.
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
        except Exception as retry_exc:
            msg = (
                f"لا يزال هناك رصيد فعلي {available:.8f} {base_asset} لكن تعذر بيعه أيضاً "
                f"(قد تكون كمية غبار صغيرة جداً دون الحد الأدنى المسموح). سنعتبرها مُغلقة "
                f"فعلياً من الناحية العملية: {retry_exc}"
            )
            logger.warning(msg)
            return ExecutionResult(dry_run=False, order=None, message=msg, already_closed=True)

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


def _cancel_open_orders(exchange: ccxt.Exchange, symbol: str) -> None:
    """يلغي كل الأوامر المعلّقة لهذا الرمز، بما فيها أوامر OCO المرتبطة (التي
    تحتاج إلغاء عبر orderListId لا عبر معرّف الأمر المفرد وحده على Binance)."""
    try:
        open_orders = exchange.fetch_open_orders(symbol)
    except Exception as exc:
        logger.warning("تعذر جلب الأوامر المعلّقة: %s", exc)
        return

    for open_order in open_orders:
        order_list_id = (open_order.get("info") or {}).get("orderListId")
        try:
            if order_list_id and str(order_list_id) != "-1":
                exchange.cancel_order(open_order["id"], symbol, params={"orderListId": order_list_id})
            else:
                exchange.cancel_order(open_order["id"], symbol)
        except Exception as exc:
            logger.warning("تعذر إلغاء الأمر المعلّق %s: %s", open_order.get("id"), exc)
