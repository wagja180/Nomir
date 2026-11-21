"""الأخبار الاقتصادية:
1) التقويم الاقتصادي (الأحداث عالية التأثير مثل NFP، قرارات الفائدة، CPI).
2) عناوين الأخبار (RSS) مع تحليل بسيط لاتجاه كل عملة (تشددي/تيسيري، قوي/ضعيف).
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from . import net

log = logging.getLogger(__name__)

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
IMPACT_RANK = {"Holiday": 0, "Low": 1, "Medium": 2, "High": 3}


@dataclass
class EconomicEvent:
    time: datetime
    currency: str
    title: str
    impact: str
    forecast: str = ""
    previous: str = ""
    actual: str = ""

    @property
    def rank(self) -> int:
        return IMPACT_RANK.get(self.impact, 0)

    def surprise(self) -> float | None:
        """الفرق بين الفعلي والمتوقع (موجب = أفضل من المتوقع عادةً)."""
        a, f = _num(self.actual), _num(self.forecast)
        if a is None or f is None:
            return None
        return a - f


def _num(s: str) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(\.\d+)?", s.replace(",", ""))
    if not m:
        return None
    v = float(m.group())
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    if s.strip() and s.strip()[-1].upper() in mult:
        v *= mult[s.strip()[-1].upper()]
    return v


def parse_calendar(items: list[dict]) -> list[EconomicEvent]:
    events = []
    for it in items:
        try:
            t = datetime.fromisoformat(it["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        events.append(EconomicEvent(
            time=t, currency=it.get("country", "").upper(), title=it.get("title", ""),
            impact=it.get("impact", "Low"), forecast=it.get("forecast", "") or "",
            previous=it.get("previous", "") or "", actual=it.get("actual", "") or "",
        ))
    return sorted(events, key=lambda e: e.time)


def fetch_calendar(url: str = CALENDAR_URL, timeout: int = 20) -> list[EconomicEvent]:
    return parse_calendar(net.get_json(url, timeout=timeout))


# ---------------- تحليل العناوين ----------------

CURRENCY_KEYWORDS = {
    "USD": ["usd", "dollar", "greenback", "fed", "fomc", "powell", "u.s.", "us ", "nfp", "payrolls"],
    "EUR": ["eur", "euro", "ecb", "lagarde", "eurozone", "germany", "german"],
    "GBP": ["gbp", "pound", "sterling", "boe", "bank of england", "uk "],
    "JPY": ["jpy", "yen", "boj", "bank of japan", "japan"],
    "CHF": ["chf", "franc", "snb", "swiss"],
    "AUD": ["aud", "aussie", "rba", "australia"],
    "CAD": ["cad", "loonie", "boc", "bank of canada", "canada"],
    "NZD": ["nzd", "kiwi", "rbnz", "new zealand"],
    "XAU": ["gold", "xau"],
}

BULLISH = ["hawkish", "rate hike", "hikes", "raise rates", "strong", "stronger", "beats",
           "surges", "jumps", "rallies", "rises", "gains", "climbs", "upbeat", "robust",
           "higher than expected", "hotter", "firm", "accelerat"]
BEARISH = ["dovish", "rate cut", "cuts rates", "cut rates", "weak", "weaker", "misses",
           "slumps", "falls", "drops", "plunges", "slides", "declines", "tumbles", "recession",
           "lower than expected", "cooler", "soft", "slows", "contraction"]


@dataclass
class Headline:
    title: str
    published: datetime | None
    link: str = ""
    scores: dict[str, int] = field(default_factory=dict)


def score_headline(title: str) -> dict[str, int]:
    """يعيد درجة لكل عملة مذكورة: موجب = إيجابي للعملة، سالب = سلبي."""
    t = " " + title.lower() + " "
    pol = sum(t.count(w) for w in BULLISH) - sum(t.count(w) for w in BEARISH)
    if pol == 0:
        return {}
    pol = 1 if pol > 0 else -1
    out = {}
    for cur, kws in CURRENCY_KEYWORDS.items():
        if any(k in t for k in kws):
            out[cur] = pol
    return out


def parse_rss(xml_text: str) -> list[Headline]:
    from email.utils import parsedate_to_datetime

    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate")
        try:
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None
        except (TypeError, ValueError):
            dt = None
        out.append(Headline(title, dt, item.findtext("link") or "", score_headline(title)))
    return out


def fetch_headlines(feeds: list[str], timeout: int = 20) -> list[Headline]:
    out: list[Headline] = []
    for url in feeds:
        try:
            out.extend(parse_rss(net.get_text(url, timeout=timeout)))
        except Exception as e:  # مصدر واحد معطل لا يوقف البوت
            log.warning("تعذّر جلب %s: %s", url, e)
    return out


class NewsMonitor:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.events: list[EconomicEvent] = []
        self.headlines: list[Headline] = []
        self.last_refresh: datetime | None = None

    def refresh(self, force: bool = False) -> None:
        now = datetime.now(timezone.utc)
        every = timedelta(minutes=self.cfg.get("refresh_minutes", 30))
        if not force and self.last_refresh and now - self.last_refresh < every:
            return
        try:
            self.events = fetch_calendar(self.cfg.get("calendar_url", CALENDAR_URL))
        except Exception as e:
            log.warning("تعذّر جلب التقويم الاقتصادي: %s", e)
        self.headlines = fetch_headlines(self.cfg.get("rss_feeds", []))
        self.last_refresh = now

    def upcoming(self, hours: float = 24, min_impact: str = "Medium",
                 now: datetime | None = None) -> list[EconomicEvent]:
        now = now or datetime.now(timezone.utc)
        lim = IMPACT_RANK[min_impact]
        return [e for e in self.events
                if e.rank >= lim and now - timedelta(hours=1) <= e.time <= now + timedelta(hours=hours)]

    def blackout(self, currencies: tuple[str, ...], now: datetime | None = None) -> EconomicEvent | None:
        """هل نحن داخل نافذة خطر حول خبر عالي التأثير يخص إحدى العملتين؟"""
        now = now or datetime.now(timezone.utc)
        before = timedelta(minutes=self.cfg.get("blackout_before_min", 30))
        after = timedelta(minutes=self.cfg.get("blackout_after_min", 30))
        lim = IMPACT_RANK[self.cfg.get("blackout_impact", "High")]
        for e in self.events:
            if e.rank >= lim and e.currency in currencies and e.time - before <= now <= e.time + after:
                return e
        return None

    def sentiment(self, currency: str, hours: float = 12, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        since = now - timedelta(hours=hours)
        return sum(h.scores.get(currency, 0) for h in self.headlines
                   if h.published is None or h.published >= since)

    def pair_bias(self, base: str, quote: str) -> int:
        """موجب = الأخبار تدعم الشراء، سالب = تدعم البيع."""
        return self.sentiment(base) - self.sentiment(quote)
