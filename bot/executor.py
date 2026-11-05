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

logger = logging.getLogger("bot.executor")


class ExecutionResult:
    def __init__(self, dry_run: bool, order: dict | None, message: str):
        self.dry_run = dry_run
        self.order = order
        self.message = message

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

    # محاولة وضع أوامر وقف الخسارة وجني الربح بعد تنفيذ الدخول (قد تختلف حسب المنصة)
    try:
        opposite_side = "sell" if side == "buy" else "buy"
        exchange.create_order(
            symbol,
            type="stop_market" if exchange.has.get("createOrder") else "stop",
            side=opposite_side,
            amount=sizing.quantity,
            params={"stopPrice": signal.stop_loss},
        )
        exchange.create_order(
            symbol,
            type="limit",
            side=opposite_side,
            amount=sizing.quantity,
            price=signal.take_profit,
        )
    except Exception as exc:  # المنصات تختلف في دعم أوامر الوقف؛ لا نوقف البوت لهذا
        logger.warning("تعذر وضع أوامر وقف الخسارة/جني الربح تلقائياً: %s", exc)

    return ExecutionResult(dry_run=False, order=order, message=f"تم تنفيذ أمر {side} حقيقي بكمية {sizing.quantity:.6f}")
