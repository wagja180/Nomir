package com.nomir.forex.core

import org.json.JSONArray
import org.json.JSONObject

data class Settings(
    val symbols: List<String> = listOf("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "EURJPY", "XAUUSD"),
    val timeframe: Timeframe = Timeframe.H1,
    val minScore: Int = 70,
    val rr: Double = 2.0,
    val slAtrMult: Double = 1.5,
    val riskPct: Double = 1.0,
    val maxOpen: Int = 3,
    val maxDailyLossPct: Double = 3.0,
    val spreadPips: Double = 1.0,
    val startBalance: Double = 10000.0,
    val autoTrade: Boolean = false,       // فتح صفقات تجريبية تلقائياً عند ظهور إشارة
    val notifySignals: Boolean = true,
    val notifyNews: Boolean = true,
    val newsBlackout: Boolean = true,
    val intervalMin: Int = 15,
) {
    fun params() = StrategyParams(minScore = minScore, rr = rr, slAtrMult = slAtrMult)

    fun toJson(): String = JSONObject().apply {
        put("symbols", JSONArray(symbols)); put("timeframe", timeframe.name); put("minScore", minScore)
        put("rr", rr); put("slAtrMult", slAtrMult); put("riskPct", riskPct); put("maxOpen", maxOpen)
        put("maxDailyLossPct", maxDailyLossPct); put("spreadPips", spreadPips); put("startBalance", startBalance)
        put("autoTrade", autoTrade); put("notifySignals", notifySignals); put("notifyNews", notifyNews)
        put("newsBlackout", newsBlackout); put("intervalMin", intervalMin)
    }.toString()

    companion object {
        fun fromJson(s: String?): Settings {
            if (s.isNullOrBlank()) return Settings()
            val o = JSONObject(s); val d = Settings()
            val syms = o.optJSONArray("symbols")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: d.symbols
            return Settings(syms,
                runCatching { Timeframe.valueOf(o.getString("timeframe")) }.getOrDefault(d.timeframe),
                o.optInt("minScore", d.minScore), o.optDouble("rr", d.rr), o.optDouble("slAtrMult", d.slAtrMult),
                o.optDouble("riskPct", d.riskPct), o.optInt("maxOpen", d.maxOpen),
                o.optDouble("maxDailyLossPct", d.maxDailyLossPct), o.optDouble("spreadPips", d.spreadPips),
                o.optDouble("startBalance", d.startBalance), o.optBoolean("autoTrade", d.autoTrade),
                o.optBoolean("notifySignals", d.notifySignals), o.optBoolean("notifyNews", d.notifyNews),
                o.optBoolean("newsBlackout", d.newsBlackout), o.optInt("intervalMin", d.intervalMin))
        }
    }
}

data class ScanItem(val state: MarketState?, val error: String? = null, val blockedBy: EconomicEvent? = null,
                    val symbol: String, val recent: List<Candle> = emptyList()) {
    /** أعلى/أدنى سعر منذ وقت معيّن (لتحديث الصفقات التجريبية). */
    fun rangeSince(t: Long): Pair<Double, Double>? {
        val last = recent.lastOrNull() ?: return null
        val bars = recent.filter { it.time >= t }
        val hi = maxOf(bars.maxOfOrNull { it.high } ?: last.close, last.close)
        val lo = minOf(bars.minOfOrNull { it.low } ?: last.close, last.close)
        return hi to lo
    }
}

object Scanner {
    /** يفحص كل الأزواج. fetch قابل للاستبدال لتسهيل الاختبار. */
    fun scan(settings: Settings, news: NewsState, now: Long,
             fetch: (String, Timeframe) -> List<Candle> = Market::candles): List<ScanItem> {
        val strat = Strategy(settings.params())
        return settings.symbols.map { sym ->
            try {
                val c = fetch(sym, settings.timeframe)
                val block = if (settings.newsBlackout)
                    news.blackout(setOf(Symbols.base(sym), Symbols.quote(sym)), now) else null
                val st = strat.analyze(c, sym, news.pairBias(sym, now))
                ScanItem(if (block != null) st?.copy(signal = null) else st, null, block, Symbols.normalize(sym),
                    c.takeLast(100))
            } catch (e: Exception) {
                ScanItem(null, e.message ?: e.javaClass.simpleName, null, Symbols.normalize(sym))
            }
        }
    }

    fun quoteToAccount(symbol: String, price: Double, prices: Map<String, Double>, acct: String = "USD"): Double {
        val b = Symbols.base(symbol); val q = Symbols.quote(symbol)
        return when {
            q == acct -> 1.0
            b == acct -> 1.0 / price
            prices[q + acct] != null -> prices[q + acct]!!
            prices[acct + q] != null -> 1.0 / prices[acct + q]!!
            else -> 1.0
        }
    }
}
