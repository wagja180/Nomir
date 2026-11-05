"""حساب حجم الصفقة بناءً على نسبة الخطر المسموحة من رأس المال."""

from dataclasses import dataclass

from bot.config import config
from bot.signals import Signal


@dataclass
class PositionSizing:
    quantity: float
    risk_amount: float
    position_value: float


def compute_position_size(balance_quote: float, signal: Signal) -> PositionSizing:
    """balance_quote: الرصيد المتاح بعملة التسعير (مثل USDT).

    المخاطرة بالمال = balance_quote * risk_per_trade، ثم تُقسم على المسافة إلى
    وقف الخسارة بالسعر لمعرفة كمية العملة (quantity) التي يمكن شراؤها/بيعها.
    """
    risk_amount = balance_quote * config.risk_per_trade
    stop_distance = abs(signal.price - signal.stop_loss)
    if stop_distance <= 0:
        return PositionSizing(quantity=0.0, risk_amount=risk_amount, position_value=0.0)

    quantity = risk_amount / stop_distance
    position_value = quantity * signal.price

    # لا يمكن أن تتجاوز قيمة الصفقة الرصيد المتاح بالكامل
    if position_value > balance_quote:
        quantity = balance_quote / signal.price
        position_value = balance_quote

    return PositionSizing(quantity=quantity, risk_amount=risk_amount, position_value=position_value)
