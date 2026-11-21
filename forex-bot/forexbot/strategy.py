"""الاستراتيجية: اتباع الاتجاه مع تأكيد الزخم وإطار زمني أعلى.

نظام نقاط (0-100):
  • الاتجاه: السعر فوق/تحت EMA200 و EMA50 فوق/تحت EMA200        (30)
  • تأكيد الإطار الأعلى (H4): ميل EMA50 في نفس الاتجاه             (20)
  • قوة الاتجاه: ADX > الحد الأدنى                                 (15)
  • الزناد: تقاطع MACD أو ارتداد RSI من منطقة التصحيح              (25)
  • RSI ليس في منطقة تشبع ضد الصفقة                                (10)
ثم تُعدّل النقاط حسب اتجاه الأخبار. الوقف والهدف مبنيان على ATR.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indicators as ta
from .data import resample


@dataclass
class Signal:
    symbol: str
    side: str            # "BUY" أو "SELL"
    entry: float
    stop_loss: float
    take_profit: float
    score: float
    time: pd.Timestamp
    reasons: list[str] = field(default_factory=list)

    @property
    def risk_reward(self) -> float:
        return abs(self.take_profit - self.entry) / abs(self.entry - self.stop_loss)


DEFAULTS = {
    "ema_fast": 50, "ema_slow": 200, "rsi_period": 14, "atr_period": 14, "adx_period": 14,
    "adx_min": 20, "rsi_pullback": 40, "rsi_overbought": 70, "rsi_oversold": 30,
    "sl_atr_mult": 1.5, "rr": 2.0, "min_score": 70, "htf_rule": "4h", "htf_ema": 50,
    "news_weight": 5,
}


class TrendMomentumStrategy:
    def __init__(self, params: dict | None = None):
        self.p = {**DEFAULTS, **(params or {})}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        d = df.copy()
        d["ema_f"] = ta.ema(d["close"], p["ema_fast"])
        d["ema_s"] = ta.ema(d["close"], p["ema_slow"])
        d["rsi"] = ta.rsi(d["close"], p["rsi_period"])
        _, _, d["macd_h"] = ta.macd(d["close"])
        d["atr"] = ta.atr(d, p["atr_period"])
        d["adx"] = ta.adx(d, p["adx_period"])
        # إطار أعلى: نستخدم فقط الشموع المكتملة (shift) لتجنب النظر للمستقبل
        try:
            htf = resample(d[["open", "high", "low", "close"]], p["htf_rule"])
            slope = ta.ema(htf["close"], p["htf_ema"]).diff().shift(1)
            d["htf_slope"] = slope.reindex(d.index, method="ffill")
        except (TypeError, ValueError):
            d["htf_slope"] = np.nan
        return d

    def signal_at(self, d: pd.DataFrame, i: int, symbol: str = "", news_bias: int = 0) -> Signal | None:
        p = self.p
        if i < max(p["ema_slow"], 30) or i >= len(d):
            return None
        r, prev = d.iloc[i], d.iloc[i - 1]
        if not np.isfinite(r["atr"]) or r["atr"] <= 0:
            return None

        for side in ("BUY", "SELL"):
            sgn = 1 if side == "BUY" else -1
            reasons, score = [], 0.0
            trend = sgn * (r["close"] - r["ema_s"]) > 0 and sgn * (r["ema_f"] - r["ema_s"]) > 0
            if not trend:
                continue
            score += 30
            reasons.append("الاتجاه العام " + ("صاعد" if sgn > 0 else "هابط") + " (EMA50/200)")

            if np.isfinite(r["htf_slope"]) and sgn * r["htf_slope"] > 0:
                score += 20
                reasons.append("الإطار الأعلى H4 يؤكد")
            if r["adx"] >= p["adx_min"]:
                score += 15
                reasons.append(f"اتجاه قوي ADX={r['adx']:.0f}")

            macd_cross = sgn * prev["macd_h"] <= 0 < sgn * r["macd_h"]
            pull = p["rsi_pullback"] if sgn > 0 else 100 - p["rsi_pullback"]
            rsi_bounce = (prev["rsi"] < pull <= r["rsi"]) if sgn > 0 else (prev["rsi"] > pull >= r["rsi"])
            if not (macd_cross or rsi_bounce):
                continue  # لا زناد = لا صفقة
            score += 25
            reasons.append("تقاطع MACD" if macd_cross else "ارتداد RSI بعد تصحيح")

            if (sgn > 0 and r["rsi"] < p["rsi_overbought"]) or (sgn < 0 and r["rsi"] > p["rsi_oversold"]):
                score += 10
            else:
                reasons.append("تحذير: RSI في منطقة تشبع")

            if news_bias:
                adj = sgn * np.sign(news_bias) * min(abs(news_bias), 3) * p["news_weight"]
                score += adj
                reasons.append(f"الأخبار {'تدعم' if adj > 0 else 'تعاكس'} الصفقة ({adj:+.0f})")

            score = float(max(0, min(100, score)))
            if score < p["min_score"]:
                return None
            entry = float(r["close"])
            sl_dist = p["sl_atr_mult"] * float(r["atr"])
            return Signal(symbol, side, entry, entry - sgn * sl_dist,
                          entry + sgn * sl_dist * p["rr"], score, d.index[i], reasons)
        return None

    def latest(self, df: pd.DataFrame, symbol: str = "", news_bias: int = 0) -> Signal | None:
        d = self.prepare(df)
        return self.signal_at(d, len(d) - 1, symbol, news_bias)
