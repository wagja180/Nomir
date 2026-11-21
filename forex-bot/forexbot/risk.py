"""إدارة المخاطر: حجم الصفقة حسب نسبة المخاطرة، حد الخسارة اليومي، عدد الصفقات."""
from __future__ import annotations

from dataclasses import dataclass

from . import symbols


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0     # نسبة من الرصيد يُخاطر بها في كل صفقة
    max_open_trades: int = 3
    max_daily_loss_pct: float = 3.0     # إيقاف التداول لليوم بعد هذه الخسارة
    max_spread_pips: float = 3.0
    min_units: int = 1000               # ميكرو لوت


def position_units(balance: float, risk_pct: float, entry: float, stop: float,
                   symbol: str, account_ccy: str = "USD", quote_to_account: float | None = None) -> int:
    """عدد الوحدات بحيث تساوي خسارة الوقف risk_pct% من الرصيد.

    الربح/الخسارة يكون بعملة التسعير (quote)، لذا نحوّله لعملة الحساب.
    """
    dist = abs(entry - stop)
    if dist <= 0:
        return 0
    base, quote = symbols.split(symbol)
    if quote_to_account is None:
        if quote == account_ccy:
            quote_to_account = 1.0
        elif base == account_ccy:
            quote_to_account = 1.0 / entry
        else:
            quote_to_account = 1.0  # تقريب؛ مرّر سعر التحويل للدقة
    risk_amount = balance * risk_pct / 100.0
    return int(risk_amount / (dist * quote_to_account) + 1e-6)


class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg

    def can_open(self, open_trades: int, day_pnl: float, balance: float,
                 symbol_already_open: bool) -> tuple[bool, str]:
        if symbol_already_open:
            return False, "يوجد صفقة مفتوحة على نفس الزوج"
        if open_trades >= self.cfg.max_open_trades:
            return False, "تم بلوغ الحد الأقصى للصفقات المفتوحة"
        if day_pnl <= -balance * self.cfg.max_daily_loss_pct / 100.0:
            return False, "تم بلوغ حد الخسارة اليومي — توقف حتى الغد"
        return True, ""
