package com.nomir.forex.core

import org.json.JSONArray
import org.w3c.dom.Element
import java.io.ByteArrayInputStream
import java.time.OffsetDateTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import javax.xml.parsers.DocumentBuilderFactory

data class EconomicEvent(
    val time: Long, // epoch seconds
    val currency: String,
    val title: String,
    val impact: String, // High / Medium / Low / Holiday
    val forecast: String = "",
    val previous: String = "",
    val actual: String = "",
) {
    val rank: Int get() = News.impactRank(impact)
}

data class Headline(val title: String, val time: Long?, val link: String, val scores: Map<String, Int>)

object News {
    const val CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    val DEFAULT_FEEDS = listOf(
        "https://www.fxstreet.com/rss/news",
        "https://www.forexlive.com/feed/news",
    )

    fun impactRank(i: String) = when (i) { "High" -> 3; "Medium" -> 2; "Low" -> 1; else -> 0 }

    fun parseCalendar(json: String): List<EconomicEvent> {
        val arr = JSONArray(json)
        val out = ArrayList<EconomicEvent>()
        for (k in 0 until arr.length()) {
            val o = arr.optJSONObject(k) ?: continue
            val t = try { OffsetDateTime.parse(o.optString("date")).toEpochSecond() } catch (e: Exception) { continue }
            out += EconomicEvent(t, o.optString("country").uppercase(), o.optString("title"),
                o.optString("impact", "Low"), o.optString("forecast"), o.optString("previous"), o.optString("actual"))
        }
        return out.sortedBy { it.time }
    }

    private val CURRENCY_KEYWORDS = mapOf(
        "USD" to listOf("usd", "dollar", "greenback", "fed", "fomc", "powell", "u.s.", " us ", "nfp", "payrolls"),
        "EUR" to listOf("eur", "euro", "ecb", "lagarde", "eurozone", "germany", "german"),
        "GBP" to listOf("gbp", "pound", "sterling", "boe", "bank of england", " uk "),
        "JPY" to listOf("jpy", "yen", "boj", "bank of japan", "japan"),
        "CHF" to listOf("chf", "franc", "snb", "swiss"),
        "AUD" to listOf("aud", "aussie", "rba", "australia"),
        "CAD" to listOf("cad", "loonie", "boc", "bank of canada", "canada"),
        "NZD" to listOf("nzd", "kiwi", "rbnz", "new zealand"),
        "XAU" to listOf("gold", "xau"),
    )
    private val BULLISH = listOf("hawkish", "rate hike", "hikes", "raise rates", "strong", "stronger", "beats",
        "surges", "jumps", "rallies", "rises", "gains", "climbs", "upbeat", "robust",
        "higher than expected", "hotter", "firm", "accelerat")
    private val BEARISH = listOf("dovish", "rate cut", "cuts rates", "cut rates", "weak", "weaker", "misses",
        "slumps", "falls", "drops", "plunges", "slides", "declines", "tumbles", "recession",
        "lower than expected", "cooler", "soft", "slows", "contraction")

    private fun count(t: String, w: String): Int {
        var n = 0; var i = t.indexOf(w)
        while (i >= 0) { n++; i = t.indexOf(w, i + w.length) }
        return n
    }

    /** موجب = إيجابي للعملة المذكورة، سالب = سلبي. */
    fun scoreHeadline(title: String): Map<String, Int> {
        val t = " " + title.lowercase() + " "
        val pol = BULLISH.sumOf { count(t, it) } - BEARISH.sumOf { count(t, it) }
        if (pol == 0) return emptyMap()
        val s = if (pol > 0) 1 else -1
        return CURRENCY_KEYWORDS.filter { (_, kws) -> kws.any { t.contains(it) } }.mapValues { s }
    }

    fun parseRss(xml: String): List<Headline> {
        val f = DocumentBuilderFactory.newInstance()
        val doc = f.newDocumentBuilder().parse(ByteArrayInputStream(xml.toByteArray(Charsets.UTF_8)))
        val items = doc.getElementsByTagName("item")
        val out = ArrayList<Headline>()
        for (k in 0 until items.length) {
            val el = items.item(k) as Element
            fun txt(tag: String) = el.getElementsByTagName(tag).item(0)?.textContent?.trim() ?: ""
            val title = txt("title")
            val time = try { ZonedDateTime.parse(txt("pubDate"), DateTimeFormatter.RFC_1123_DATE_TIME).toEpochSecond() }
                       catch (e: Exception) { null }
            out += Headline(title, time, txt("link"), scoreHeadline(title))
        }
        return out
    }
}

class NewsState(val events: List<EconomicEvent>, val headlines: List<Headline>) {

    fun upcoming(now: Long, hours: Double = 24.0, minImpact: Int = 2) =
        events.filter { it.rank >= minImpact && it.time >= now - 3600 && it.time <= now + (hours * 3600).toLong() }

    /** خبر عالي التأثير خلال نافذة الخطر لإحدى العملتين؟ */
    fun blackout(currencies: Set<String>, now: Long, beforeMin: Int = 30, afterMin: Int = 30): EconomicEvent? =
        events.firstOrNull { it.rank >= 3 && it.currency in currencies &&
            now >= it.time - beforeMin * 60 && now <= it.time + afterMin * 60 }

    fun sentiment(currency: String, now: Long, hours: Int = 12): Int =
        headlines.filter { it.time == null || it.time >= now - hours * 3600 }.sumOf { it.scores[currency] ?: 0 }

    fun pairBias(symbol: String, now: Long) =
        sentiment(Symbols.base(symbol), now) - sentiment(Symbols.quote(symbol), now)
}
