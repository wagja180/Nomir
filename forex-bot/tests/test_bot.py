import json
import math
import random
from datetime import datetime, timedelta, timezone

import pytest

from forexbot import indicators as ta
from forexbot.backtest import run_backtest
from forexbot.broker import PaperBroker
from forexbot.candles import Candle, resample
from forexbot.data import CsvProvider, _parse_time, parse_yahoo
from forexbot.news import NewsMonitor, parse_calendar, parse_rss, score_headline
from forexbot.risk import RiskConfig, RiskManager, position_units
from forexbot.strategy import TrendMomentumStrategy


def synthetic(n=3000, drift=0.00003, seed=1, start=1.10):
    rng = random.Random(seed)
    px, out = start, []
    for i in range(n):
        regime = 1 if math.sin(i / 400.0) >= 0 else -1  # اتجاهات متناوبة
        o = px
        px *= math.exp(drift * regime + rng.gauss(0, 0.0012))
        hi = max(o, px) * (1 + abs(rng.gauss(0, 0.0005)))
        lo = min(o, px) * (1 - abs(rng.gauss(0, 0.0005)))
        out.append(Candle(1735689600 + i * 3600, o, hi, lo, px))
    return out


def test_indicators_ranges():
    c = synthetic(500)
    close = [x.close for x in c]
    assert all(0 <= v <= 100 for v in ta.rsi(close))
    assert all(v > 0 for v in ta.atr(c))
    assert all(0 <= v <= 100 for v in ta.adx(c))
    assert ta.ema([5.0] * 50, 10)[-1] == pytest.approx(5.0)
    lo, mid, hi = ta.bollinger(close)
    assert lo[30] < mid[30] < hi[30]


def test_strategy_signals_are_consistent():
    s = TrendMomentumStrategy({"min_score": 60})
    d = s.prepare(synthetic())
    sigs = [x for i in range(len(d)) if (x := s.signal_at(d, i, "EURUSD"))]
    assert sigs, "يجب أن تظهر إشارات على بيانات ذات اتجاه"
    assert {x.side for x in sigs} == {"BUY", "SELL"}
    for x in sigs:
        if x.side == "BUY":
            assert x.stop_loss < x.entry < x.take_profit
        else:
            assert x.take_profit < x.entry < x.stop_loss
        assert x.risk_reward == pytest.approx(2.0)
        assert 60 <= x.score <= 100


def test_no_lookahead_in_htf():
    c = synthetic(1200)
    full = ta.htf_slope(c, 14400, 50)
    part = ta.htf_slope(c[:800], 14400, 50)
    for a, b in zip(part, full[:800]):
        assert (math.isnan(a) and math.isnan(b)) or a == pytest.approx(b)


def test_backtest_runs():
    res = run_backtest(synthetic(), "EURUSD", TrendMomentumStrategy({"min_score": 60}))
    st = res.stats()
    assert st["trades"] > 0
    for t in res.trades:
        assert t.r_multiple == pytest.approx(2.0) or t.r_multiple == pytest.approx(-1.0)


def test_position_sizing():
    assert position_units(10000, 1, 1.1000, 1.0980, "EURUSD") == 50000
    assert position_units(10000, 1, 150.0, 149.8, "USDJPY") == 75000


def test_risk_manager():
    rm = RiskManager(RiskConfig(max_open_trades=2, max_daily_loss_pct=3))
    assert rm.can_open(0, 0, 10000, False)[0]
    assert not rm.can_open(2, 0, 10000, False)[0]
    assert not rm.can_open(0, -301, 10000, False)[0]
    assert not rm.can_open(0, 0, 10000, True)[0]


def test_paper_broker(tmp_path):
    b = PaperBroker(str(tmp_path / "s.json"), 10000, spread_pips=0)
    b.market_order("EURUSD", "BUY", 10000, 1.0980, 1.1040, 1.1000)
    assert not b.update("EURUSD", 1.1010, 1.0990, 1.1000)
    closed = b.update("EURUSD", 1.1045, 1.1000, 1.1040)
    assert closed[0].pnl == pytest.approx(40.0)
    assert b.balance == pytest.approx(10040.0)
    assert json.loads((tmp_path / "s.json").read_text())["balance"] == pytest.approx(10040.0)


def test_news_calendar_and_blackout():
    now = datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc)
    ev = parse_calendar([
        {"title": "Non-Farm Employment Change", "country": "USD", "impact": "High",
         "date": (now + timedelta(minutes=20)).isoformat(), "forecast": "180K", "previous": "150K"},
        {"title": "German Ifo", "country": "EUR", "impact": "Medium",
         "date": (now + timedelta(hours=3)).isoformat()},
    ])
    m = NewsMonitor({})
    m.events = ev
    assert m.blackout(("EUR", "USD"), now).currency == "USD"
    assert m.blackout(("EUR", "JPY"), now) is None
    assert len(m.upcoming(24, "Medium", now)) == 2
    ev[0].actual = "250K"
    assert ev[0].surprise() == pytest.approx(70000)


def test_headline_sentiment():
    assert score_headline("Fed signals hawkish stance, dollar rallies") == {"USD": 1}
    assert score_headline("ECB cuts rates as euro slides")["EUR"] == -1
    rss = """<rss><channel><item><title>BoJ hawkish surprise lifts yen</title>
    <pubDate>Fri, 20 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
    m = NewsMonitor({})
    m.headlines = parse_rss(rss)
    assert m.sentiment("JPY", now=datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc)) == 1


def test_parsers_and_resample(tmp_path):
    js = {"chart": {"result": [{"timestamp": [0, 3600, 7200, 10800, 14400],
          "indicators": {"quote": [{"open": [1, 2, 3, None, 5], "high": [2, 3, 4, 5, 6],
                                    "low": [.5, 1.5, 2.5, 3.5, 4.5], "close": [2, 3, 4, 5, 6]}]}}]}}
    c = parse_yahoo(js)
    assert len(c) == 4
    r = resample(c, 14400)
    assert [(x.open, x.high, x.close) for x in r] == [(1, 4, 4), (5, 6, 6)]
    assert _parse_time("2024-01-01T00:00:00.000000000Z") == 1704067200
    (tmp_path / "EURUSD_H1.csv").write_text("time,open,high,low,close\n"
                                            "2024-01-01 01:00:00,1,2,0.5,1.5\n2024-01-01 00:00:00,1,2,0.5,1.2\n")
    rows = CsvProvider(str(tmp_path)).candles("EURUSD", "H1")
    assert [x.close for x in rows] == [1.2, 1.5]


def test_spread_is_a_real_cost():
    c = synthetic()
    s = TrendMomentumStrategy({"min_score": 60})
    cheap = run_backtest(c, "EURUSD", s, spread_pips=0).stats()
    wide = run_backtest(c, "EURUSD", s, spread_pips=20).stats()
    assert wide["net_profit"] < cheap["net_profit"]


def test_telegram_placeholder_disabled(monkeypatch):
    from forexbot.notifier import Notifier
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "الرمز")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "الرقم")
    assert Notifier().telegram is False
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-def_1")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654")
    assert Notifier().telegram is True


def test_max_trades_per_day():
    c = synthetic()
    s = TrendMomentumStrategy({"min_score": 50, "rr": 0.5})
    res = run_backtest(c, "EURUSD", s, spread_pips=0, max_trades_per_day=1)
    days = [t.entry_time // 86400 for t in res.trades]
    # الحد يُطبّق على يوم الإشارة؛ الدخول قد يقع في الشمعة التالية (بداية اليوم التالي)
    assert all(days.count(d) <= 2 for d in days)
    unlimited = run_backtest(c, "EURUSD", s, spread_pips=0)
    assert len(res.trades) <= len(unlimited.trades)
    assert res.stats()["trades_per_day"] > 0
    rm = RiskManager(RiskConfig(max_trades_per_day=1))
    assert not rm.can_open(0, 0, 10000, False, trades_today=1)[0]
    assert rm.can_open(0, 0, 10000, False, trades_today=0)[0]
