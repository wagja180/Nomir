"""أدوات أزواج العملات."""
from __future__ import annotations


def normalize(symbol: str) -> str:
    """'eur/usd' أو 'EUR_USD' أو 'EURUSD=X' → 'EURUSD'."""
    s = symbol.upper().replace("/", "").replace("_", "").replace("=X", "")
    return s


def split(symbol: str) -> tuple[str, str]:
    s = normalize(symbol)
    return s[:3], s[3:6]


def pip_size(symbol: str) -> float:
    base, quote = split(symbol)
    if quote == "JPY":
        return 0.01
    if base in ("XAU",):
        return 0.1
    if base in ("XAG",):
        return 0.01
    return 0.0001


def to_yahoo(symbol: str) -> str:
    s = normalize(symbol)
    # Yahoo لا يوفر XAUUSD=X بشكل موثوق، نستخدم العقود الآجلة للذهب والفضة
    return {"XAUUSD": "GC=F", "XAGUSD": "SI=F"}.get(s, s + "=X")


def to_oanda(symbol: str) -> str:
    b, q = split(symbol)
    return f"{b}_{q}"
