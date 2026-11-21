"""مصادر بيانات الأسعار: Yahoo Finance (مجاني)، OANDA (حساب تجريبي/حقيقي)، أو ملف CSV."""
from __future__ import annotations

import logging
import os

import pandas as pd
import requests

from . import symbols

log = logging.getLogger(__name__)

# إطار زمني موحّد → صيغ المزودين
_YAHOO_INTERVAL = {"M15": "15m", "M30": "30m", "H1": "60m", "H4": "60m", "D1": "1d"}
_YAHOO_RANGE = {"M15": "60d", "M30": "60d", "H1": "730d", "H4": "730d", "D1": "10y"}
_RESAMPLE = {"M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1D"}

OHLC = ["open", "high", "low", "close"]


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


class PriceProvider:
    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> pd.DataFrame:
        raise NotImplementedError

    def last_price(self, symbol: str) -> float:
        return float(self.candles(symbol, "M15", 5)["close"].iloc[-1])


class YahooProvider(PriceProvider):
    URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"

    def __init__(self, timeout: int = 20):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (forexbot)"
        self.timeout = timeout

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> pd.DataFrame:
        params = {"interval": _YAHOO_INTERVAL[timeframe], "range": _YAHOO_RANGE[timeframe]}
        r = self.session.get(self.URL.format(sym=symbols.to_yahoo(symbol)), params=params,
                             timeout=self.timeout)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        df = pd.DataFrame(
            {k: q[k] for k in OHLC},
            index=pd.to_datetime(res["timestamp"], unit="s", utc=True),
        ).dropna()
        if timeframe == "H4":
            df = resample(df, "4h")
        return df.tail(count)


class OandaProvider(PriceProvider):
    def __init__(self, token: str | None = None, practice: bool = True, timeout: int = 20):
        self.token = token or os.environ.get("OANDA_TOKEN", "")
        if not self.token:
            raise ValueError("OANDA_TOKEN غير مضبوط")
        host = "api-fxpractice.oanda.com" if practice else "api-fxtrade.oanda.com"
        self.base = f"https://{host}/v3"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.timeout = timeout

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 500) -> pd.DataFrame:
        gran = {"M15": "M15", "M30": "M30", "H1": "H1", "H4": "H4", "D1": "D"}[timeframe]
        r = self.session.get(
            f"{self.base}/instruments/{symbols.to_oanda(symbol)}/candles",
            params={"granularity": gran, "count": min(count, 5000), "price": "M"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        rows = [
            {"time": c["time"], **{k: float(c["mid"][k[0]]) for k in OHLC}}
            for c in r.json()["candles"] if c.get("complete", True)
        ]
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df.pop("time"), utc=True)
        return df


class CsvProvider(PriceProvider):
    """ملفات CSV بأعمدة: time,open,high,low,close — اسم الملف {SYMBOL}_{TF}.csv"""

    def __init__(self, folder: str):
        self.folder = folder

    def candles(self, symbol: str, timeframe: str = "H1", count: int = 100000) -> pd.DataFrame:
        path = os.path.join(self.folder, f"{symbols.normalize(symbol)}_{timeframe}.csv")
        df = pd.read_csv(path)
        df.columns = [c.lower() for c in df.columns]
        tcol = next(c for c in ("time", "date", "datetime", "timestamp") if c in df.columns)
        df.index = pd.to_datetime(df.pop(tcol), utc=True)
        return df[OHLC].astype(float).sort_index().tail(count)


def make_provider(cfg: dict) -> PriceProvider:
    name = cfg.get("provider", "yahoo").lower()
    if name == "yahoo":
        return YahooProvider()
    if name == "oanda":
        return OandaProvider(practice=cfg.get("oanda_practice", True))
    if name == "csv":
        return CsvProvider(cfg.get("csv_folder", "data"))
    raise ValueError(f"مزود غير معروف: {name}")
