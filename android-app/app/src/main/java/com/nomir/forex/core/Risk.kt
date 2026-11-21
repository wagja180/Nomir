package com.nomir.forex.core

import kotlin.math.abs

object Risk {
    /** عدد الوحدات بحيث تساوي خسارة الوقف riskPct% من الرصيد. */
    fun positionUnits(balance: Double, riskPct: Double, entry: Double, stop: Double, symbol: String,
                      accountCcy: String = "USD", quoteToAccount: Double? = null): Long {
        val dist = abs(entry - stop)
        if (dist <= 0) return 0
        val q2a = quoteToAccount ?: when (accountCcy) {
            Symbols.quote(symbol) -> 1.0
            Symbols.base(symbol) -> 1.0 / entry
            else -> 1.0
        }
        return (balance * riskPct / 100.0 / (dist * q2a) + 1e-6).toLong()
    }

    fun canOpen(openTrades: Int, maxOpen: Int, dayPnl: Double, balance: Double, maxDailyLossPct: Double,
                symbolOpen: Boolean): String? = when {
        symbolOpen -> "يوجد صفقة مفتوحة على نفس الزوج"
        openTrades >= maxOpen -> "تم بلوغ الحد الأقصى للصفقات المفتوحة"
        dayPnl <= -balance * maxDailyLossPct / 100.0 -> "تم بلوغ حد الخسارة اليومي"
        else -> null
    }
}
