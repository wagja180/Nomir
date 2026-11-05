"""جلب بيانات الشموع (OHLCV) من منصة التداول عبر ccxt."""

import ccxt
import pandas as pd

from bot.config import config


def build_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, config.exchange_id)
    exchange = exchange_class(
        {
            "apiKey": config.api_key or None,
            "secret": config.api_secret or None,
            "enableRateLimit": True,
        }
    )
    if config.sandbox and exchange.has.get("sandbox"):
        exchange.set_sandbox_mode(True)
    return exchange


def fetch_ohlcv(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str = "4h",
    limit: int = 300,
    since: int | None = None,
) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=since)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df
