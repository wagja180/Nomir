"""مصادر الأسعار: Yahoo Finance (مجاني)، OANDA، أو ملف CSV — بدون pandas."""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone

from . import net, symbols
from .candles import Candle, resample

log = logging.getLogger(__name__)

_YAHOO_INTERVAL = {"M15": "15m", "M30": "30m", "H1": "60m", "H4": "60m", "D1": "1d"}
_YAHOO_RANGE = {"M15": "60d", "M30": "60d", "H1": "730d", "H4": "730d", "D1": "10y"}


def _parse_time(s: str) -> int:
    s = s.strip()
    if s.replace(".", "", 1).isdigit():
        return int(float(s))
    s = s.replace("Z", "+00:00")
    if "." in s:  # OANDA يرسل 9 خانات بعد الفاصلة
        head, rest = s.split(".", 1)
        frac = "".join(ch for ch in rest if ch.isdigit())
        tz = rest[len(frac):]
        s = f"{head}.{frac[:6]}{tz}"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def parse_yahoo(js: dict) -> list[Candle]:
    res = js["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(res.get("timestamp") or []):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        out.append(Candle(int(t), float(o), float(h), float(l), float(c)))
    return out


class PriceProvider:
    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> list[Candle]:
        raise NotImplementedError

    def last_price(self, symbol: str) -> float:
        return self.candles(symbol, "M15", 5)[-1].close


class YahooProvider(PriceProvider):
    URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> list[Candle]:
        js = net.get_json(self.URL.format(sym=symbols.to_yahoo(symbol)),
                          params={"interval": _YAHOO_INTERVAL[timeframe], "range": _YAHOO_RANGE[timeframe]})
        c = parse_yahoo(js)
        if timeframe == "H4":
            c = resample(c, 4 * 3600)
        return c[-count:]


class OandaProvider(PriceProvider):
    def __init__(self, token: str | None = None, practice: bool = True):
        self.token = token or os.environ.get("OANDA_TOKEN", "")
        if not self.token:
            raise ValueError("OANDA_TOKEN غير مضبوط")
        host = "api-fxpractice.oanda.com" if practice else "api-fxtrade.oanda.com"
        self.base = f"https://{host}/v3"

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> list[Candle]:
        gran = {"M15": "M15", "M30": "M30", "H1": "H1", "H4": "H4", "D1": "D"}[timeframe]
        js = net.get_json(f"{self.base}/instruments/{symbols.to_oanda(symbol)}/candles",
                          params={"granularity": gran, "count": min(count, 5000), "price": "M"},
                          headers={"Authorization": f"Bearer {self.token}"})
        return [Candle(_parse_time(c["time"]), *(float(c["mid"][k]) for k in "ohlc"))
                for c in js["candles"] if c.get("complete", True)]


class CsvProvider(PriceProvider):
    """ملفات CSV بأعمدة: time,open,high,low,close — اسم الملف {SYMBOL}_{TF}.csv"""

    def __init__(self, folder: str):
        self.folder = folder

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 10**9) -> list[Candle]:
        path = os.path.join(self.folder, f"{symbols.normalize(symbol)}_{timeframe}.csv")
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        out = []
        for r in rows:
            r = {k.lower().strip(): v for k, v in r.items()}
            tkey = next(k for k in ("time", "date", "datetime", "timestamp") if k in r)
            out.append(Candle(_parse_time(r[tkey]), float(r["open"]), float(r["high"]),
                              float(r["low"]), float(r["close"])))
        out.sort(key=lambda c: c.time)
        return out[-count:]


def make_provider(cfg: dict) -> PriceProvider:
    name = cfg.get("provider", "yahoo").lower()
    if name == "yahoo":
        return YahooProvider()
    if name == "oanda":
        return OandaProvider(practice=cfg.get("oanda_practice", True))
    if name == "csv":
        return CsvProvider(cfg.get("csv_folder", "data"))
    raise ValueError(f"مزود غير معروف: {name}")
