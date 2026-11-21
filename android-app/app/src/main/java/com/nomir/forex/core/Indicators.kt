package com.nomir.forex.core

import kotlin.math.abs
import kotlin.math.max

object Indicators {
    private fun smooth(x: DoubleArray, alpha: Double): DoubleArray {
        val y = DoubleArray(x.size)
        if (x.isEmpty()) return y
        y[0] = x[0]
        for (i in 1 until x.size) y[i] = alpha * x[i] + (1 - alpha) * y[i - 1]
        return y
    }

    fun ema(x: DoubleArray, n: Int) = smooth(x, 2.0 / (n + 1))
    fun wilder(x: DoubleArray, n: Int) = smooth(x, 1.0 / n)

    fun rsi(close: DoubleArray, n: Int = 14): DoubleArray {
        val g = DoubleArray(close.size)
        val l = DoubleArray(close.size)
        for (i in 1 until close.size) {
            val d = close[i] - close[i - 1]
            g[i] = max(d, 0.0); l[i] = max(-d, 0.0)
        }
        val ag = wilder(g, n)
        val al = wilder(l, n)
        return DoubleArray(close.size) { i -> if (al[i] == 0.0) 100.0 else 100 - 100 / (1 + ag[i] / al[i]) }
    }

    fun macdHist(close: DoubleArray, fast: Int = 12, slow: Int = 26, signal: Int = 9): DoubleArray {
        val f = ema(close, fast)
        val s = ema(close, slow)
        val line = DoubleArray(close.size) { f[it] - s[it] }
        val sig = ema(line, signal)
        return DoubleArray(close.size) { line[it] - sig[it] }
    }

    fun trueRange(c: List<Candle>) = DoubleArray(c.size) { i ->
        if (i == 0) c[0].high - c[0].low
        else maxOf(c[i].high - c[i].low, abs(c[i].high - c[i - 1].close), abs(c[i].low - c[i - 1].close))
    }

    fun atr(c: List<Candle>, n: Int = 14) = wilder(trueRange(c), n)

    fun adx(c: List<Candle>, n: Int = 14): DoubleArray {
        val pdm = DoubleArray(c.size)
        val mdm = DoubleArray(c.size)
        for (i in 1 until c.size) {
            val up = c[i].high - c[i - 1].high
            val down = c[i - 1].low - c[i].low
            if (up > down && up > 0) pdm[i] = up
            if (down > up && down > 0) mdm[i] = down
        }
        val tr = atr(c, n)
        val sp = wilder(pdm, n)
        val sm = wilder(mdm, n)
        val dx = DoubleArray(c.size) { i ->
            if (tr[i] == 0.0) 0.0 else {
                val p = 100 * sp[i] / tr[i]
                val m = 100 * sm[i] / tr[i]
                if (p + m == 0.0) 0.0 else 100 * abs(p - m) / (p + m)
            }
        }
        return wilder(dx, n)
    }

    /** ميل EMA على إطار أعلى (مثلاً 4 ساعات) باستخدام الشموع المكتملة فقط — بدون نظر للمستقبل. */
    fun htfSlope(c: List<Candle>, bucketSec: Long, n: Int): DoubleArray {
        if (c.isEmpty()) return DoubleArray(0)
        val keys = c.map { Math.floorDiv(it.time, bucketSec) }
        val bucketKeys = ArrayList<Long>()
        val bucketClose = ArrayList<Double>()
        for (i in c.indices) {
            if (bucketKeys.isEmpty() || bucketKeys.last() != keys[i]) {
                bucketKeys.add(keys[i]); bucketClose.add(c[i].close)
            } else bucketClose[bucketClose.size - 1] = c[i].close
        }
        val e = ema(bucketClose.toDoubleArray(), n)
        val idx = HashMap<Long, Int>()
        bucketKeys.forEachIndexed { j, k -> idx[k] = j }
        return DoubleArray(c.size) { i ->
            val j = idx[keys[i]]!!
            if (j >= 2) e[j - 1] - e[j - 2] else Double.NaN
        }
    }
}
