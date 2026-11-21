package com.nomir.forex.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.exp
import kotlin.math.sin
import kotlin.math.abs
import java.util.Random

class CoreTest {
    private fun synthetic(n: Int = 3000, seed: Long = 1, start: Double = 1.10): List<Candle> {
        val r = Random(seed)
        var px = start
        val out = ArrayList<Candle>()
        for (i in 0 until n) {
            val regime = Math.signum(sin(i / 400.0))
            val o = px
            px *= exp(0.00003 * regime + r.nextGaussian() * 0.0012)
            val hi = maxOf(o, px) * (1 + abs(r.nextGaussian()) * 0.0005)
            val lo = minOf(o, px) * (1 - abs(r.nextGaussian()) * 0.0005)
            out += Candle(1735689600L + i * 3600L, o, hi, lo, px)
        }
        return out
    }

    @Test fun indicatorsInRange() {
        val c = synthetic(600)
        val close = DoubleArray(c.size) { c[it].close }
        assertTrue(Indicators.rsi(close).all { it in 0.0..100.0 })
        assertTrue(Indicators.adx(c).all { it in 0.0..100.0 })
        assertTrue(Indicators.atr(c).all { it > 0 })
        // EMA ثابتة على سلسلة ثابتة
        assertEquals(5.0, Indicators.ema(DoubleArray(50) { 5.0 }, 10).last(), 1e-12)
    }

    @Test fun signalsConsistent() {
        val s = Strategy(StrategyParams(minScore = 60))
        val d = s.prepare(synthetic())
        val sigs = (d.c.indices).mapNotNull { s.signalAt(d, it, "EURUSD") }
        assertTrue(sigs.isNotEmpty())
        assertEquals(setOf("BUY", "SELL"), sigs.map { it.side }.toSet())
        for (x in sigs) {
            if (x.side == "BUY") assertTrue(x.stopLoss < x.entry && x.entry < x.takeProfit)
            else assertTrue(x.takeProfit < x.entry && x.entry < x.stopLoss)
            assertEquals(2.0, x.riskReward, 1e-9)
            assertTrue(x.score in 60..100)
        }
    }

    @Test fun htfNoLookahead() {
        val c = synthetic(1200)
        val full = Indicators.htfSlope(c, 14400, 50)
        val part = Indicators.htfSlope(c.take(800), 14400, 50)
        for (i in 0 until 800) if (part[i].isFinite()) assertEquals(part[i], full[i], 1e-15)
    }

    @Test fun sizing() {
        assertEquals(50000L, Risk.positionUnits(10000.0, 1.0, 1.1000, 1.0980, "EURUSD"))
        assertEquals(75000L, Risk.positionUnits(10000.0, 1.0, 150.0, 149.8, "USDJPY"))
        assertNull(Risk.canOpen(0, 3, 0.0, 10000.0, 3.0, false))
        assertNotNull(Risk.canOpen(3, 3, 0.0, 10000.0, 3.0, false))
        assertNotNull(Risk.canOpen(0, 3, -301.0, 10000.0, 3.0, false))
    }

    @Test fun paperBookRoundTrip() {
        val b = PaperBook(10000.0)
        val sig = Signal("EURUSD", "BUY", 1.1000, 1.0980, 1.1040, 80, 0, listOf())
        b.openTrade(sig, 10000, 0.0, 100)
        assertTrue(b.update("EURUSD", 1.1010, 1.0990, 200).isEmpty())
        val closed = b.update("EURUSD", 1.1045, 1.1000, 300)
        assertEquals(40.0, closed[0].pnl, 1e-6)
        val r = PaperBook.fromJson(b.toJson())
        assertEquals(10040.0, r.balance, 1e-6)
        assertEquals(1, r.history.size)
        assertEquals(100.0, r.winRate(), 1e-9)
    }

    @Test fun newsCalendarBlackoutSentiment() {
        val json = """[{"title":"Non-Farm Employment Change","country":"USD","date":"2026-11-20T08:30:00-05:00","impact":"High","forecast":"180K","previous":"150K"},
                       {"title":"German Ifo","country":"EUR","date":"2026-11-20T04:00:00-05:00","impact":"Medium"}]"""
        val ev = News.parseCalendar(json)
        assertEquals("EUR", ev[0].currency)
        val nfp = ev[1].time
        val ns = NewsState(ev, News.parseRss("""<rss><channel><item><title>Fed signals hawkish stance, dollar rallies</title>
            <pubDate>Fri, 20 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>"""))
        assertEquals("USD", ns.blackout(setOf("EUR", "USD"), nfp - 600)?.currency)
        assertNull(ns.blackout(setOf("EUR", "JPY"), nfp - 600))
        assertNull(ns.blackout(setOf("USD"), nfp + 3600))
        assertEquals(1, ns.sentiment("USD", nfp))
        assertEquals(-1, ns.pairBias("EURUSD", nfp))
        assertEquals(mapOf("EUR" to -1), News.scoreHeadline("ECB cuts rates as euro slides"))
    }

    @Test fun yahooParseAndResample() {
        val json = """{"chart":{"result":[{"timestamp":[0,3600,7200,10800,14400],
          "indicators":{"quote":[{"open":[1,2,3,null,5],"high":[2,3,4,5,6],"low":[0.5,1.5,2.5,3.5,4.5],"close":[2,3,4,5,6]}]}}]}}"""
        val c = Market.parseYahoo(json)
        assertEquals(4, c.size)
        val r = Market.resample(c, 14400)
        assertEquals(2, r.size)
        assertEquals(1.0, r[0].open, 0.0); assertEquals(4.0, r[0].high, 0.0); assertEquals(4.0, r[0].close, 0.0)
    }

    @Test fun scannerWithFakeFetch() {
        val data = synthetic()
        val s = Settings(symbols = listOf("EURUSD", "BAD"), minScore = 0)
        val items = Scanner.scan(s, NewsState(emptyList(), emptyList()), 0) { sym, _ ->
            if (sym == "BAD") throw RuntimeException("boom") else data }
        assertNotNull(items[0].state)
        assertEquals("boom", items[1].error)
        assertEquals(s, Settings.fromJson(s.toJson()))
    }
}
