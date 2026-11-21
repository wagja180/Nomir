"""الشمعة اليابانية وأدوات بسيطة عليها."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class Candle:
    time: int      # بالثواني (UTC)
    open: float
    high: float
    low: float
    close: float


def resample(candles: list[Candle], seconds: int) -> list[Candle]:
    out: list[Candle] = []
    key = None
    for c in candles:
        k = c.time // seconds
        if out and k == key:
            cur = out[-1]
            cur.high = max(cur.high, c.high)
            cur.low = min(cur.low, c.low)
            cur.close = c.close
        else:
            key = k
            out.append(Candle(k * seconds, c.open, c.high, c.low, c.close))
    return out


def fmt_time(t: int, pattern: str = "%Y-%m-%d %H:%M") -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime(pattern)
