"""اكتشاف مناطق العرض والطلب (الدعم والمقاومة) من بيانات الشموع.

المبدأ:
1. إيجاد القمم والقيعان المحلية (swing highs / swing lows) باستخدام نافذة انزلاقية.
2. تجميع القمم القريبة من بعضها في "مناطق مقاومة/عرض"، والقيعان في "مناطق دعم/طلب".
3. كل منطقة تحمل عدد مرات الارتداد عنها (قوتها) ومدى حداثتها، وتُستخدم كمرجع لصفقات
   الشراء (عند الدعم) والبيع (عند المقاومة).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Zone:
    kind: str  # "demand" (دعم/شراء) أو "supply" (مقاومة/بيع)
    low: float
    high: float
    touches: int = 1
    last_index: int = 0

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high

    def distance_pct(self, price: float) -> float:
        """نسبة المسافة من السعر إلى أقرب حد للمنطقة (0 إذا كان السعر داخلها)."""
        if self.contains(price):
            return 0.0
        nearest = self.low if price < self.low else self.high
        return abs(price - nearest) / nearest


def _find_swings(df: pd.DataFrame, window: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """يعيد مواضع القمم والقيعان المحلية (fractals) بنافذة window على كل جانب."""
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    swing_high_idx, swing_low_idx = [], []

    for i in range(window, n - window):
        local_highs = highs[i - window : i + window + 1]
        local_lows = lows[i - window : i + window + 1]
        if highs[i] == local_highs.max():
            swing_high_idx.append(i)
        if lows[i] == local_lows.min():
            swing_low_idx.append(i)

    return np.array(swing_high_idx), np.array(swing_low_idx)


def _cluster_points(
    df: pd.DataFrame, indices: np.ndarray, price_col: str, kind: str, tolerance_pct: float
) -> list[Zone]:
    """يجمع نقاط القمم/القيعان القريبة من بعضها (ضمن tolerance_pct) في مناطق واحدة."""
    if len(indices) == 0:
        return []

    prices = df[price_col].values[indices]
    order = np.argsort(prices)
    sorted_prices = prices[order]
    sorted_idx = indices[order]

    zones: list[Zone] = []
    current_prices = [sorted_prices[0]]
    current_indices = [sorted_idx[0]]

    def flush():
        lo, hi = min(current_prices), max(current_prices)
        zones.append(
            Zone(
                kind=kind,
                low=float(lo),
                high=float(hi) if hi > lo else float(lo) * 1.0005,
                touches=len(current_prices),
                last_index=int(max(current_indices)),
            )
        )

    for p, idx in zip(sorted_prices[1:], sorted_idx[1:]):
        ref = np.mean(current_prices)
        if abs(p - ref) / ref <= tolerance_pct:
            current_prices.append(p)
            current_indices.append(idx)
        else:
            flush()
            current_prices = [p]
            current_indices = [idx]
    flush()

    return zones


def detect_zones(
    df: pd.DataFrame,
    swing_window: int = 3,
    tolerance_pct: float = 0.004,
    min_touches: int = 1,
    max_zones_per_side: int = 6,
) -> list[Zone]:
    """يستخرج مناطق العرض (مقاومة) والطلب (دعم) من بيانات الشموع.

    tolerance_pct: النسبة المسموحة لاعتبار قمتين/قاعدتين جزءاً من نفس المنطقة.
    min_touches: أقل عدد ارتدادات لقبول المنطقة (المناطق الأقوى لها أولوية أعلى).
    """
    swing_high_idx, swing_low_idx = _find_swings(df, window=swing_window)

    supply_zones = _cluster_points(df, swing_high_idx, "high", "supply", tolerance_pct)
    demand_zones = _cluster_points(df, swing_low_idx, "low", "demand", tolerance_pct)

    zones = [z for z in supply_zones + demand_zones if z.touches >= min_touches]

    supply = sorted([z for z in zones if z.kind == "supply"], key=lambda z: (-z.touches, -z.last_index))
    demand = sorted([z for z in zones if z.kind == "demand"], key=lambda z: (-z.touches, -z.last_index))

    return supply[:max_zones_per_side] + demand[:max_zones_per_side]


def nearest_zone(zones: list[Zone], price: float, kind: str | None = None) -> Zone | None:
    candidates = zones if kind is None else [z for z in zones if z.kind == kind]
    if not candidates:
        return None
    return min(candidates, key=lambda z: z.distance_pct(price))
