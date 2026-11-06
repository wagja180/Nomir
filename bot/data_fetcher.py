"""جلب بيانات الشموع (OHLCV) من منصة التداول عبر ccxt."""

import os

import ccxt
import pandas as pd

from bot.config import config


def _apply_system_proxy(exchange: ccxt.Exchange) -> None:
    """ccxt يتجاهل متغيرات البيئة الخاصة بالبروكسي افتراضياً (trust_env=False)،
    فإذا كانت بيئة التشغيل تتطلب بروكسي صادر (HTTPS_PROXY) تُطبَّق هنا يدوياً،
    وإلا يفشل الاتصال بخطأ DNS مضلّل بدلاً من استخدام البروكسي الصحيح."""
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if not proxy_url:
        return
    exchange.session.trust_env = True
    exchange.session.proxies = {"https": proxy_url, "http": proxy_url}
    ca_bundle = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
    if ca_bundle and os.path.exists(ca_bundle):
        exchange.session.verify = ca_bundle


def build_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, config.exchange_id)
    exchange = exchange_class(
        {
            "apiKey": config.api_key or None,
            "secret": config.api_secret or None,
            "enableRateLimit": True,
        }
    )
    _apply_system_proxy(exchange)
    if config.sandbox and exchange.has.get("sandbox"):
        exchange.set_sandbox_mode(True)
        _apply_system_proxy(exchange)  # set_sandbox_mode يبدّل عنوان الـ API وقد يعيد تهيئة الجلسة
    return exchange


def fetch_quote_balance(exchange: ccxt.Exchange, symbol: str) -> float:
    """الرصيد المتاح (الحر) بعملة التسعير (مثل USDT في BTC/USDT) من المنصة فعلياً."""
    quote = symbol.split("/")[1]
    balance = exchange.fetch_balance()
    return float(balance.get("free", {}).get(quote) or 0.0)


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
