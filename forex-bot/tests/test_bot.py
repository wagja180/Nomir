import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from forexbot import indicators as ta
from forexbot.backtest import run_backtest
from forexbot.broker import PaperBroker
from forexbot.news import NewsMonitor, parse_calendar, parse_rss, score_headline
from forexbot.risk import RiskConfig, RiskManager, position_units
from forexbot.strategy import TrendMomentumStrategy


def synthetic(n=3000, drift=0.00003, seed=1, start=1.10):
    rng = np.random.default_rng(seed)
    # اتجاهات متناوبة لإنتاج إشارات في الاتجاهين
    regime = np.sign(np.sin(np.arange(n) / 400.0))
    rets = drift * regime + rng.normal(0, 0.0012, n)
    close = start * np.exp(np.cumsum(rets))
    open_ = np.r_[close[0], close[:-1]]
    hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0005, n)))
    lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0005, n)))
    idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close}, index=idx)


def test_indicators_ranges():
    df = synthetic(500)
    r = ta.rsi(df["close"])
    assert r.between(0, 100).all()
    assert (ta.atr(df) > 0).iloc[1:].all()
    assert ta.adx(df).between(0, 100).all()


def test_strategy_signals_are_consistent():
    df = synthetic()
    s = TrendMomentumStrategy({"min_score": 60})
    d = s.prepare(df)
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
    df = synthetic(1200)
    s = TrendMomentumStrategy()
    full = s.prepare(df)["htf_slope"]
    part = s.prepare(df.iloc[:800])["htf_slope"]
    pd.testing.assert_series_equal(full.iloc[:800], part, check_names=False)


def test_backtest_runs():
    res = run_backtest(synthetic(), "EURUSD", TrendMomentumStrategy({"min_score": 60}))
    st = res.stats()
    assert st["trades"] > 0
    for t in res.trades:
        assert t.r_multiple == pytest.approx(2.0, abs=1e-6) or t.r_multiple == pytest.approx(-1.0, abs=1e-6)


def test_position_sizing():
    # EURUSD: وقف 20 نقطة، رصيد 10000، مخاطرة 1% = 100$ → 50,000 وحدة
    assert position_units(10000, 1, 1.1000, 1.0980, "EURUSD") == 50000
    # USDJPY: وقف 0.20 ين @150 → خسارة لكل وحدة 0.2/150 $
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
    now = datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc)
    assert m.sentiment("JPY", now=now) == 1
