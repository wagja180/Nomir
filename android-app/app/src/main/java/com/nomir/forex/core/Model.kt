package com.nomir.forex.core

data class Candle(val time: Long, val open: Double, val high: Double, val low: Double, val close: Double)

data class Signal(
    val symbol: String,
    val side: String, // BUY / SELL
    val entry: Double,
    val stopLoss: Double,
    val takeProfit: Double,
    val score: Int,
    val time: Long,
    val reasons: List<String>,
) {
    val riskReward: Double get() = Math.abs(takeProfit - entry) / Math.abs(entry - stopLoss)
}

object Symbols {
    fun normalize(s: String) = s.uppercase().replace("/", "").replace("_", "").replace("=X", "")
    fun base(s: String) = normalize(s).take(3)
    fun quote(s: String) = normalize(s).drop(3).take(3)
    fun pip(s: String): Double = when {
        quote(s) == "JPY" -> 0.01
        base(s) == "XAU" -> 0.1
        base(s) == "XAG" -> 0.01
        else -> 0.0001
    }
    fun digits(s: String): Int = when {
        quote(s) == "JPY" -> 3
        base(s) == "XAU" || base(s) == "XAG" -> 2
        else -> 5
    }
    fun yahoo(s: String) = when (normalize(s)) {
        "XAUUSD" -> "GC=F"   // الذهب (عقود آجلة) — Yahoo لا يوفر XAUUSD=X بشكل موثوق
        "XAGUSD" -> "SI=F"
        else -> normalize(s) + "=X"
    }
    fun fmt(s: String, v: Double) = String.format(java.util.Locale.US, "%.${digits(s)}f", v)
}
