package com.nomir.forex.core

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object Net {
    fun get(url: String, timeoutMs: Int = 20000): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = timeoutMs; c.readTimeout = timeoutMs
        c.setRequestProperty("User-Agent", "Mozilla/5.0 (Android; NomirForex)")
        try {
            if (c.responseCode !in 200..299) throw RuntimeException("HTTP ${c.responseCode}")
            return c.inputStream.bufferedReader().use { it.readText() }
        } finally { c.disconnect() }
    }
}

enum class Timeframe(val label: String, val yahooInterval: String, val yahooRange: String, val resampleSec: Long?) {
    M15("15 دقيقة", "15m", "60d", null),
    H1("ساعة", "60m", "60d", null),
    H4("4 ساعات", "60m", "730d", 4 * 3600),
    D1("يوم", "1d", "5y", null),
}

object Market {
    fun parseYahoo(json: String): List<Candle> {
        val res = JSONObject(json).getJSONObject("chart").getJSONArray("result").getJSONObject(0)
        val ts = res.getJSONArray("timestamp")
        val q = res.getJSONObject("indicators").getJSONArray("quote").getJSONObject(0)
        val o = q.getJSONArray("open"); val h = q.getJSONArray("high")
        val l = q.getJSONArray("low"); val c = q.getJSONArray("close")
        val out = ArrayList<Candle>(ts.length())
        for (i in 0 until ts.length()) {
            if (o.isNull(i) || h.isNull(i) || l.isNull(i) || c.isNull(i)) continue
            out += Candle(ts.getLong(i), o.getDouble(i), h.getDouble(i), l.getDouble(i), c.getDouble(i))
        }
        return out
    }

    fun resample(c: List<Candle>, sec: Long): List<Candle> {
        val out = ArrayList<Candle>()
        var cur: Candle? = null
        var key = Long.MIN_VALUE
        for (x in c) {
            val k = Math.floorDiv(x.time, sec)
            if (cur == null || k != key) {
                cur?.let { out += it }
                key = k; cur = Candle(k * sec, x.open, x.high, x.low, x.close)
            } else cur = cur.copy(high = maxOf(cur.high, x.high), low = minOf(cur.low, x.low), close = x.close)
        }
        cur?.let { out += it }
        return out
    }

    fun candles(symbol: String, tf: Timeframe): List<Candle> {
        val url = "https://query1.finance.yahoo.com/v8/finance/chart/${Symbols.yahoo(symbol)}" +
            "?interval=${tf.yahooInterval}&range=${tf.yahooRange}"
        val raw = parseYahoo(Net.get(url))
        return tf.resampleSec?.let { resample(raw, it) } ?: raw
    }

    fun fetchNews(feeds: List<String>): NewsState {
        val events = try { News.parseCalendar(Net.get(News.CALENDAR_URL)) } catch (e: Exception) { emptyList() }
        val heads = feeds.flatMap { u -> try { News.parseRss(Net.get(u)) } catch (e: Exception) { emptyList() } }
        return NewsState(events, heads.sortedByDescending { it.time ?: 0 })
    }
}
