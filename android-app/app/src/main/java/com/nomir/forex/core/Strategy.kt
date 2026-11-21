package com.nomir.forex.core

import kotlin.math.abs
import kotlin.math.min
import kotlin.math.sign

data class StrategyParams(
    val emaFast: Int = 50,
    val emaSlow: Int = 200,
    val adxMin: Double = 20.0,
    val rsiPullback: Double = 40.0,
    val rsiOverbought: Double = 70.0,
    val rsiOversold: Double = 30.0,
    val slAtrMult: Double = 1.5,
    val rr: Double = 2.0,
    val minScore: Int = 70,
    val htfBucketSec: Long = 4 * 3600,
    val htfEma: Int = 50,
    val newsWeight: Int = 5,
)

/** حالة السوق الحالية لكل زوج (تُعرض في الواجهة حتى بدون إشارة). */
data class MarketState(
    val symbol: String,
    val price: Double,
    val changePct: Double,
    val trend: Int,   // 1 صاعد، -1 هابط، 0 عرضي
    val rsi: Double,
    val adx: Double,
    val signal: Signal?,
)

class Prepared(val c: List<Candle>, p: StrategyParams) {
    val close = DoubleArray(c.size) { c[it].close }
    val emaF = Indicators.ema(close, p.emaFast)
    val emaS = Indicators.ema(close, p.emaSlow)
    val rsi = Indicators.rsi(close)
    val macdH = Indicators.macdHist(close)
    val atr = Indicators.atr(c)
    val adx = Indicators.adx(c)
    val htf = Indicators.htfSlope(c, p.htfBucketSec, p.htfEma)
}

/**
 * اتباع الاتجاه + زخم + تأكيد إطار أعلى. نظام نقاط من 100:
 * الاتجاه 30، الإطار الأعلى 20، ADX 15، الزناد (إلزامي) 25، RSI غير متشبع 10، الأخبار ±15.
 */
class Strategy(val p: StrategyParams = StrategyParams()) {

    fun prepare(c: List<Candle>) = Prepared(c, p)

    fun signalAt(d: Prepared, i: Int, symbol: String, newsBias: Int = 0): Signal? {
        if (i < maxOf(p.emaSlow, 30) || i >= d.c.size) return null
        val atr = d.atr[i]
        if (!atr.isFinite() || atr <= 0) return null
        val close = d.close[i]
        for (sgn in intArrayOf(1, -1)) {
            val reasons = ArrayList<String>()
            var score = 0.0
            val trend = sgn * (close - d.emaS[i]) > 0 && sgn * (d.emaF[i] - d.emaS[i]) > 0
            if (!trend) continue
            score += 30; reasons += "الاتجاه العام " + (if (sgn > 0) "صاعد" else "هابط") + " (EMA50/200)"
            if (d.htf[i].isFinite() && sgn * d.htf[i] > 0) { score += 20; reasons += "الإطار الأعلى H4 يؤكد" }
            if (d.adx[i] >= p.adxMin) { score += 15; reasons += "اتجاه قوي ADX=${d.adx[i].toInt()}" }

            val macdCross = sgn * d.macdH[i - 1] <= 0 && 0 < sgn * d.macdH[i]
            val pull = if (sgn > 0) p.rsiPullback else 100 - p.rsiPullback
            val rsiBounce = if (sgn > 0) d.rsi[i - 1] < pull && pull <= d.rsi[i]
                            else d.rsi[i - 1] > pull && pull >= d.rsi[i]
            if (!(macdCross || rsiBounce)) continue
            score += 25; reasons += if (macdCross) "تقاطع MACD" else "ارتداد RSI بعد تصحيح"

            if ((sgn > 0 && d.rsi[i] < p.rsiOverbought) || (sgn < 0 && d.rsi[i] > p.rsiOversold)) score += 10
            else reasons += "تحذير: RSI في منطقة تشبع"

            if (newsBias != 0) {
                val adj = sgn * sign(newsBias.toDouble()) * min(abs(newsBias), 3) * p.newsWeight
                score += adj
                reasons += "الأخبار ${if (adj > 0) "تدعم" else "تعاكس"} الصفقة (${if (adj > 0) "+" else ""}${adj.toInt()})"
            }
            val s = score.coerceIn(0.0, 100.0).toInt()
            if (s < p.minScore) return null
            val dist = p.slAtrMult * atr
            return Signal(Symbols.normalize(symbol), if (sgn > 0) "BUY" else "SELL", close,
                close - sgn * dist, close + sgn * dist * p.rr, s, d.c[i].time, reasons)
        }
        return null
    }

    fun analyze(c: List<Candle>, symbol: String, newsBias: Int = 0): MarketState? {
        if (c.size < 2) return null
        val d = prepare(c)
        val i = c.size - 1
        val trend = when {
            d.close[i] > d.emaS[i] && d.emaF[i] > d.emaS[i] -> 1
            d.close[i] < d.emaS[i] && d.emaF[i] < d.emaS[i] -> -1
            else -> 0
        }
        // التغير خلال ~24 شمعة
        val ref = d.close[maxOf(0, i - 24)]
        return MarketState(Symbols.normalize(symbol), d.close[i], 100 * (d.close[i] - ref) / ref,
            trend, d.rsi[i], d.adx[i], signalAt(d, i, symbol, newsBias))
    }
}
