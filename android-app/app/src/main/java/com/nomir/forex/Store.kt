package com.nomir.forex

import android.content.Context
import com.nomir.forex.core.PaperBook
import com.nomir.forex.core.Settings

/** تخزين محلي بسيط على الهاتف. */
class Store(ctx: Context) {
    private val sp = ctx.applicationContext.getSharedPreferences("nomir_forex", Context.MODE_PRIVATE)

    var settings: Settings
        get() = Settings.fromJson(sp.getString("settings", null))
        set(v) = sp.edit().putString("settings", v.toJson()).apply()

    var book: PaperBook
        get() = PaperBook.fromJson(sp.getString("book", null)).also {
            if (!sp.contains("book")) it.balance = settings.startBalance
        }
        set(v) = sp.edit().putString("book", v.toJson()).apply()

    var lastRun: Long
        get() = sp.getLong("lastRun", 0)
        set(v) = sp.edit().putLong("lastRun", v).apply()

    /** مفاتيح التنبيهات المرسلة سابقاً حتى لا تتكرر. */
    fun alreadyNotified(key: String): Boolean {
        val set = sp.getStringSet("notified", emptySet())!!
        if (key in set) return true
        val next = (set + key).toList().takeLast(300).toSet()
        sp.edit().putStringSet("notified", next).apply()
        return false
    }
}
