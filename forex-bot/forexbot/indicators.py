"""المؤشرات الفنية بدون numpy/pandas: EMA, RSI, MACD, ATR, ADX, Bollinger."""
from __future__ import annotations

import math

from .candles import Candle


def _smooth(x: list[float], alpha: float) -> list[float]:
    out = []
    prev = None
    for v in x:
        prev = v if prev is None else alpha * v + (1 - alpha) * prev
        out.append(prev)
    return out


def ema(x: list[float], n: int) -> list[float]:
    return _smooth(x, 2.0 / (n + 1))


def wilder(x: list[float], n: int) -> list[float]:
    return _smooth(x, 1.0 / n)


def rsi(close: list[float], n: int = 14) -> list[float]:
    gains, losses = [0.0], [0.0]
    for i in range(1, len(close)):
        d = close[i] - close[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag, al = wilder(gains, n), wilder(losses, n)
    return [100.0 if l == 0 else 100 - 100 / (1 + g / l) for g, l in zip(ag, al)]


def macd(close: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    f, s = ema(close, fast), ema(close, slow)
    line = [a - b for a, b in zip(f, s)]
    sig = ema(line, signal)
    return line, sig, [a - b for a, b in zip(line, sig)]


def true_range(c: list[Candle]) -> list[float]:
    out = []
    for i, x in enumerate(c):
        if i == 0:
            out.append(x.high - x.low)
        else:
            pc = c[i - 1].close
            out.append(max(x.high - x.low, abs(x.high - pc), abs(x.low - pc)))
    return out


def atr(c: list[Candle], n: int = 14) -> list[float]:
    return wilder(true_range(c), n)


def adx(c: list[Candle], n: int = 14) -> list[float]:
    pdm, mdm = [0.0], [0.0]
    for i in range(1, len(c)):
        up = c[i].high - c[i - 1].high
        down = c[i - 1].low - c[i].low
        pdm.append(up if up > down and up > 0 else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
    tr, sp, sm = atr(c, n), wilder(pdm, n), wilder(mdm, n)
    dx = []
    for t, p, m in zip(tr, sp, sm):
        if t == 0:
            dx.append(0.0)
            continue
        pdi, mdi = 100 * p / t, 100 * m / t
        dx.append(0.0 if pdi + mdi == 0 else 100 * abs(pdi - mdi) / (pdi + mdi))
    return wilder(dx, n)


def bollinger(close: list[float], n: int = 20, k: float = 2.0):
    lo, mid, hi = [], [], []
    for i in range(len(close)):
        if i < n - 1:
            lo.append(math.nan); mid.append(math.nan); hi.append(math.nan)
            continue
        w = close[i - n + 1:i + 1]
        m = sum(w) / n
        sd = math.sqrt(sum((v - m) ** 2 for v in w) / (n - 1))
        lo.append(m - k * sd); mid.append(m); hi.append(m + k * sd)
    return lo, mid, hi


def htf_slope(c: list[Candle], bucket_sec: int, n: int) -> list[float]:
    """ميل EMA على إطار أعلى (مثلاً 4 ساعات) من الشموع المكتملة فقط — بدون نظر للمستقبل."""
    keys = [x.time // bucket_sec for x in c]
    bkeys, bclose = [], []
    for k, x in zip(keys, c):
        if bkeys and bkeys[-1] == k:
            bclose[-1] = x.close
        else:
            bkeys.append(k); bclose.append(x.close)
    e = ema(bclose, n)
    idx = {k: j for j, k in enumerate(bkeys)}
    out = []
    for k in keys:
        j = idx[k]
        out.append(e[j - 1] - e[j - 2] if j >= 2 else math.nan)
    return out
