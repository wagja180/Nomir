package com.nomir.forex.core

import org.json.JSONArray
import org.json.JSONObject

data class Position(
    val id: String,
    val symbol: String,
    val side: String,
    val units: Long,
    val entry: Double,
    val stopLoss: Double,
    val takeProfit: Double,
    val openedAt: Long,
    val closedAt: Long? = null,
    val exit: Double? = null,
    val pnl: Double = 0.0,
    val reason: String = "",
) {
    fun floating(price: Double, q2a: Double = 1.0) = (if (side == "BUY") 1 else -1) * (price - entry) * units * q2a

    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id); put("symbol", symbol); put("side", side); put("units", units)
        put("entry", entry); put("sl", stopLoss); put("tp", takeProfit); put("openedAt", openedAt)
        closedAt?.let { put("closedAt", it) }; exit?.let { put("exit", it) }
        put("pnl", pnl); put("reason", reason)
    }

    companion object {
        fun fromJson(o: JSONObject) = Position(
            o.getString("id"), o.getString("symbol"), o.getString("side"), o.getLong("units"),
            o.getDouble("entry"), o.getDouble("sl"), o.getDouble("tp"), o.getLong("openedAt"),
            if (o.has("closedAt")) o.getLong("closedAt") else null,
            if (o.has("exit")) o.getDouble("exit") else null,
            o.optDouble("pnl", 0.0), o.optString("reason"))
    }
}

/** محفظة التداول التجريبي (بمال وهمي). */
class PaperBook(var balance: Double = 10000.0, val open: MutableList<Position> = mutableListOf(),
                val history: MutableList<Position> = mutableListOf(), var seq: Int = 0) {

    fun openTrade(sig: Signal, units: Long, spreadPips: Double, now: Long): Position {
        val half = spreadPips * Symbols.pip(sig.symbol) / 2
        val fill = if (sig.side == "BUY") sig.entry + half else sig.entry - half
        val p = Position("P${++seq}", sig.symbol, sig.side, units, fill, sig.stopLoss, sig.takeProfit, now)
        open += p
        return p
    }

    /** يغلق الصفقات التي لمست الوقف أو الهدف (إذا لُمسا معاً نحتسب الوقف تحفّظاً). */
    fun update(symbol: String, high: Double, low: Double, now: Long, q2a: Double = 1.0): List<Position> {
        val closed = ArrayList<Position>()
        for (p in open.toList()) {
            if (p.symbol != Symbols.normalize(symbol)) continue
            val buy = p.side == "BUY"
            val hitSl = if (buy) low <= p.stopLoss else high >= p.stopLoss
            val hitTp = if (buy) high >= p.takeProfit else low <= p.takeProfit
            if (hitSl || hitTp) closed += close(p, if (hitSl) p.stopLoss else p.takeProfit,
                if (hitSl) "وقف الخسارة" else "جني الربح", now, q2a)
        }
        return closed
    }

    fun close(p: Position, price: Double, reason: String, now: Long, q2a: Double = 1.0): Position {
        val c = p.copy(closedAt = now, exit = price, pnl = p.floating(price, q2a), reason = reason)
        open.remove(p); history.add(0, c); balance += c.pnl
        return c
    }

    fun dayPnl(dayStart: Long) = history.filter { (it.closedAt ?: 0) >= dayStart }.sumOf { it.pnl }

    fun winRate(): Double = if (history.isEmpty()) 0.0 else 100.0 * history.count { it.pnl > 0 } / history.size

    fun toJson(): String = JSONObject().apply {
        put("balance", balance); put("seq", seq)
        put("open", JSONArray(open.map { it.toJson() }))
        put("history", JSONArray(history.take(500).map { it.toJson() }))
    }.toString()

    fun reset(balance: Double) { this.balance = balance; open.clear(); history.clear(); seq = 0 }

    companion object {
        fun fromJson(s: String?): PaperBook {
            if (s.isNullOrBlank()) return PaperBook()
            val o = JSONObject(s)
            fun list(k: String) = o.optJSONArray(k)?.let { a -> (0 until a.length()).map { Position.fromJson(a.getJSONObject(it)) } } ?: emptyList()
            return PaperBook(o.optDouble("balance", 10000.0), list("open").toMutableList(),
                list("history").toMutableList(), o.optInt("seq"))
        }
    }
}
