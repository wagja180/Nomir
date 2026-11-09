"""توليد إشارات شراء/بيع بدمج مناطق العرض والطلب مع المؤشرات الفنية.

شرط الشراء: السعر داخل/قريب من منطقة طلب (دعم) + RSI ليس في تشبع شرائي +
            شمعة الإغلاق الحالية صاعدة (إغلاق أعلى من الافتتاح) تؤكد الارتداد.
شرط البيع: السعر داخل/قريب من منطقة عرض (مقاومة) + RSI ليس في تشبع بيعي +
           شمعة الإغلاق الحالية نازلة تؤكد الرفض.

يتم أيضاً احتساب وقف الخسارة (على حد المنطقة مع هامش ATR) والهدف (أقرب منطقة
معاكسة أو نسبة مكافأة/خطر دنيا) لكل إشارة.
"""

from dataclasses import dataclass

import pandas as pd

from bot.config import config
from bot.zones import Zone, nearest_zone


@dataclass
class Signal:
    side: str  # "buy" أو "sell"
    price: float
    stop_loss: float
    take_profit: float
    zone: Zone
    reason: str

    @property
    def reward_risk_ratio(self) -> float:
        risk = abs(self.price - self.stop_loss)
        reward = abs(self.take_profit - self.price)
        return reward / risk if risk > 0 else 0.0


ZONE_PROXIMITY_PCT = 0.006  # يعتبر السعر "قريباً" من المنطقة ضمن 0.6%


def generate_signal(df: pd.DataFrame, zones: list[Zone]) -> Signal | None:
    if len(df) < 210:
        return None  # غير كافٍ لحساب EMA200 بثقة

    last = df.iloc[-1]
    price = float(last["close"])
    atr_val = float(last["atr_14"]) if not pd.isna(last["atr_14"]) else price * 0.01

    bullish_candle = last["close"] > last["open"]
    bearish_candle = last["close"] < last["open"]
    uptrend = last["ema_50"] > last["ema_200"]
    downtrend = last["ema_50"] < last["ema_200"]

    demand = nearest_zone(zones, price, kind="demand")
    supply = nearest_zone(zones, price, kind="supply")

    # --- محاولة إشارة شراء عند منطقة طلب ---
    if demand and demand.distance_pct(price) <= ZONE_PROXIMITY_PCT:
        near_demand = demand.contains(price) or price <= demand.high * (1 + ZONE_PROXIMITY_PCT)
        if near_demand and bullish_candle and last["rsi_14"] < 65 and uptrend:
            stop_loss = demand.low - atr_val * 0.5
            target_zone = supply if supply and supply.mid > price else None
            take_profit = target_zone.low if target_zone else price + (price - stop_loss) * config.min_reward_risk_ratio
            sig = Signal(
                side="buy",
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                zone=demand,
                reason=(
                    f"السعر عند منطقة طلب/دعم ({demand.low:.4f}-{demand.high:.4f}, "
                    f"قوة {demand.touches} ارتدادات)، شمعة صاعدة، RSI={last['rsi_14']:.1f}، "
                    f"الاتجاه العام صاعد (EMA50>EMA200)."
                ),
            )
            if sig.reward_risk_ratio >= config.min_reward_risk_ratio:
                return sig

    # --- محاولة إشارة بيع عند منطقة عرض ---
    if supply and supply.distance_pct(price) <= ZONE_PROXIMITY_PCT:
        near_supply = supply.contains(price) or price >= supply.low * (1 - ZONE_PROXIMITY_PCT)
        if near_supply and bearish_candle and last["rsi_14"] > 35 and downtrend:
            stop_loss = supply.high + atr_val * 0.5
            target_zone = demand if demand and demand.mid < price else None
            take_profit = target_zone.high if target_zone else price - (stop_loss - price) * config.min_reward_risk_ratio
            sig = Signal(
                side="sell",
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                zone=supply,
                reason=(
                    f"السعر عند منطقة عرض/مقاومة ({supply.low:.4f}-{supply.high:.4f}, "
                    f"قوة {supply.touches} ارتدادات)، شمعة نازلة، RSI={last['rsi_14']:.1f}، "
                    f"الاتجاه العام نازل (EMA50<EMA200)."
                ),
            )
            if sig.reward_risk_ratio >= config.min_reward_risk_ratio:
                return sig

    return None
