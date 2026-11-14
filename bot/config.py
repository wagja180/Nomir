import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    val = os.getenv(name)
    return float(val) if val else default


def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val else default


@dataclass
class Config:
    exchange_id: str = os.getenv("EXCHANGE_ID", "binance")
    api_key: str = os.getenv("EXCHANGE_API_KEY", "")
    api_secret: str = os.getenv("EXCHANGE_API_SECRET", "")
    # بعض المنصات (مثل OKX) تتطلب كلمة مرور إضافية (Passphrase) بجانب
    # المفتاح والسر؛ تُترك فارغة لمنصات مثل Binance التي لا تحتاجها.
    api_passphrase: str = os.getenv("EXCHANGE_API_PASSPHRASE", "")
    sandbox: bool = _bool("EXCHANGE_SANDBOX", True)
    risk_per_trade: float = _float("RISK_PER_TRADE", 0.01)
    max_open_positions: int = _int("MAX_OPEN_POSITIONS", 1)
    min_reward_risk_ratio: float = _float("MIN_REWARD_RISK_RATIO", 1.5)
    # أقصى مسافة (نسبة من السعر) تُعتبر فيها الشمعة "قريبة" من منطقة عرض/طلب
    # لقبول إشارة. توسيعها يزيد عدد الإشارات لكن يضعف دقة نقطة الدخول.
    zone_proximity_pct: float = _float("ZONE_PROXIMITY_PCT", 0.006)
    # هل تُشترط موافقة الإشارة لاتجاه EMA50/EMA200 العام؟ تعطيلها يزيد عدد
    # الإشارات (يسمح بالتداول عكس الاتجاه العام) لكنه أخطر عادة.
    require_trend_alignment: bool = _bool("REQUIRE_TREND_ALIGNMENT", True)

    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)


config = Config()
