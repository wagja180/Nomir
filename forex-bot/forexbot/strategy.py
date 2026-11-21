"""الاستراتيجية: اتباع الاتجاه مع تأكيد الزخم وإطار زمني أعلى.

نظام نقاط (0-100):
  • الاتجاه: السعر و EMA50 فوق/تحت EMA200                         (30)
  • تأكيد الإطار الأعلى (H4): ميل EMA50 في نفس الاتجاه             (20)
  • قوة الاتجاه: ADX > الحد الأدنى                                 (15)
  • الزناد (إلزامي): تقاطع MACD أو ارتداد RSI من منطقة التصحيح     (25)
  • RSI ليس في منطقة تشبع ضد الصفقة                                (10)
ثم تُعدّل النقاط حسب اتجاه الأخبار. الوقف والهدف مبنيان على ATR.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import indicators as ta
from . import symbols
from .candles import Candle


@dataclass
class Signal:
    symbol: str
    side: str            # "BUY" أو "SELL"
    entry: float
    stop_loss: float
    take_profit: float
    score: float
    time: int
    reasons: list[str] = field(default_factory=list)

    @property
    def risk_reward(self) -> float:
        return abs(self.take_profit - self.entry) / abs(self.entry - self.stop_loss)


DEFAULTS = {
    "ema_fast": 50, "ema_slow": 200, "rsi_period": 14, "atr_period": 14, "adx_period": 14,
    "adx_min": 20, "rsi_pullback": 40, "rsi_overbought": 70, "rsi_oversold": 30,
    "sl_atr_mult": 1.5, "rr": 2.0, "min_score": 70, "htf_hours": 4, "htf_ema": 50,
    "news_weight": 5,
}


class Prepared:
    """كل المؤشرات محسوبة مسبقاً على قائمة الشموع."""

    def __init__(self, candles: list[Candle], p: dict):
        self.c = candles
        self.close = [x.close for x in candles]
        self.ema_f = ta.ema(self.close, p["ema_fast"])
        self.ema_s = ta.ema(self.close, p["ema_slow"])
        self.rsi = ta.rsi(self.close, p["rsi_period"])
        _, _, self.macd_h = ta.macd(self.close)
        self.atr = ta.atr(candles, p["atr_period"])
        self.adx = ta.adx(candles, p["adx_period"])
        self.htf = ta.htf_slope(candles, int(p["htf_hours"] * 3600), p["htf_ema"])

    def __len__(self):
        return len(self.c)


class TrendMomentumStrategy:
    def __init__(self, params: dict | None = None):
        self.p = {**DEFAULTS, **(params or {})}

    def prepare(self, candles: list[Candle]) -> Prepared:
        return Prepared(candles, self.p)

    def signal_at(self, d: Prepared, i: int, symbol: str = "", news_bias: int = 0) -> Signal | None:
        p = self.p
        if i < max(p["ema_slow"], 30) or i >= len(d):
            return None
        atr = d.atr[i]
        if not math.isfinite(atr) or atr <= 0:
            return None
        close = d.close[i]

        for sgn in (1, -1):
            reasons, score = [], 0.0
            if not (sgn * (close - d.ema_s[i]) > 0 and sgn * (d.ema_f[i] - d.ema_s[i]) > 0):
                continue
            score += 30
            reasons.append("الاتجاه العام " + ("صاعد" if sgn > 0 else "هابط") + " (EMA50/200)")
            if math.isfinite(d.htf[i]) and sgn * d.htf[i] > 0:
                score += 20
                reasons.append("الإطار الأعلى H4 يؤكد")
            if d.adx[i] >= p["adx_min"]:
                score += 15
                reasons.append(f"اتجاه قوي ADX={d.adx[i]:.0f}")

            macd_cross = sgn * d.macd_h[i - 1] <= 0 < sgn * d.macd_h[i]
            pull = p["rsi_pullback"] if sgn > 0 else 100 - p["rsi_pullback"]
            r0, r1 = d.rsi[i - 1], d.rsi[i]
            rsi_bounce = (r0 < pull <= r1) if sgn > 0 else (r0 > pull >= r1)
            if not (macd_cross or rsi_bounce):
                continue  # لا زناد = لا صفقة
            score += 25
            reasons.append("تقاطع MACD" if macd_cross else "ارتداد RSI بعد تصحيح")

            if (sgn > 0 and r1 < p["rsi_overbought"]) or (sgn < 0 and r1 > p["rsi_oversold"]):
                score += 10
            else:
                reasons.append("تحذير: RSI في منطقة تشبع")

            if news_bias:
                adj = sgn * (1 if news_bias > 0 else -1) * min(abs(news_bias), 3) * p["news_weight"]
                score += adj
                reasons.append(f"الأخبار {'تدعم' if adj > 0 else 'تعاكس'} الصفقة ({adj:+.0f})")

            score = max(0.0, min(100.0, score))
            if score < p["min_score"]:
                return None
            dist = p["sl_atr_mult"] * atr
            return Signal(symbols.normalize(symbol) if symbol else "", "BUY" if sgn > 0 else "SELL",
                          close, close - sgn * dist, close + sgn * dist * p["rr"], score, d.c[i].time, reasons)
        return None

    def latest(self, candles: list[Candle], symbol: str = "", news_bias: int = 0) -> Signal | None:
        d = self.prepare(candles)
        return self.signal_at(d, len(d) - 1, symbol, news_bias)
