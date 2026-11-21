package com.nomir.forex

import android.content.Context
import com.nomir.forex.core.Market
import com.nomir.forex.core.News
import com.nomir.forex.core.NewsState
import com.nomir.forex.core.PaperBook
import com.nomir.forex.core.Position
import com.nomir.forex.core.Risk
import com.nomir.forex.core.ScanItem
import com.nomir.forex.core.Scanner
import com.nomir.forex.core.Signal
import com.nomir.forex.core.Symbols
import java.time.LocalDate
import java.time.ZoneOffset

data class CycleResult(val items: List<ScanItem>, val news: NewsState, val book: PaperBook, val time: Long)

/** دورة كاملة: أخبار ← فحص الأزواج ← تحديث الصفقات ← تنبيهات/تداول تلقائي. */
object Engine {

    fun prices(items: List<ScanItem>) = items.mapNotNull { i -> i.state?.let { i.symbol to it.price } }.toMap()

    fun q2a(symbol: String, price: Double, items: List<ScanItem>) =
        Scanner.quoteToAccount(symbol, price, prices(items))

    fun signalText(s: Signal, units: Long? = null): String {
        val pip = Symbols.pip(s.symbol)
        val sb = StringBuilder()
        sb.append("الدخول ${Symbols.fmt(s.symbol, s.entry)}\n")
        sb.append("الوقف ${Symbols.fmt(s.symbol, s.stopLoss)} (${(Math.abs(s.entry - s.stopLoss) / pip).toInt()} نقطة)\n")
        sb.append("الهدف ${Symbols.fmt(s.symbol, s.takeProfit)} (${(Math.abs(s.takeProfit - s.entry) / pip).toInt()} نقطة)\n")
        units?.let { sb.append("الحجم ${"%,d".format(it)} وحدة\n") }
        s.reasons.forEach { sb.append("• ").append(it).append('\n') }
        return sb.toString().trim()
    }

    fun tryOpen(store: Store, book: PaperBook, sig: Signal, items: List<ScanItem>, now: Long): Pair<Position?, String?> {
        val st = store.settings
        val dayStart = LocalDate.now(ZoneOffset.UTC).atStartOfDay().toEpochSecond(ZoneOffset.UTC)
        Risk.canOpen(book.open.size, st.maxOpen, book.dayPnl(dayStart), book.balance, st.maxDailyLossPct,
            book.open.any { it.symbol == sig.symbol })?.let { return null to it }
        val units = Risk.positionUnits(book.balance, st.riskPct, sig.entry, sig.stopLoss, sig.symbol,
            quoteToAccount = q2a(sig.symbol, sig.entry, items))
        val minUnits = if (Symbols.base(sig.symbol) in setOf("XAU", "XAG")) 1L else 1000L
        if (units < minUnits) return null to "حجم الصفقة أصغر من الحد الأدنى ($minUnits وحدة)"
        return book.openTrade(sig, units, st.spreadPips, now) to null
    }

    fun cycle(ctx: Context, background: Boolean): CycleResult {
        val store = Store(ctx)
        val st = store.settings
        val now = System.currentTimeMillis() / 1000
        val news = Market.fetchNews(News.DEFAULT_FEEDS)
        val items = Scanner.scan(st, news, now)
        val book = store.book

        // 1) تحديث الصفقات المفتوحة
        for (p in book.open.toList()) {
            val it = items.firstOrNull { x -> x.symbol == p.symbol } ?: continue
            val (hi, lo) = it.rangeSince(p.openedAt) ?: continue
            for (c in book.update(p.symbol, hi, lo, now, q2a(p.symbol, it.state?.price ?: p.entry, items))) {
                Notifier.send(ctx, Notifier.CH_TRADES, c.id.hashCode(),
                    "${if (c.pnl >= 0) "✅" else "❌"} إغلاق ${c.symbol} — ${c.reason}",
                    "الربح/الخسارة: ${"%+.2f".format(c.pnl)} $")
            }
        }

        // 2) الإشارات الجديدة
        for (item in items) {
            val sig = item.state?.signal ?: continue
            val key = "sig:${sig.symbol}:${sig.time}:${sig.side}"
            if (store.alreadyNotified(key)) continue
            var units: Long? = null
            var note = ""
            if (st.autoTrade) {
                val (pos, why) = tryOpen(store, book, sig, items, now)
                units = pos?.units
                note = if (pos != null) "\n📌 فُتحت صفقة تجريبية تلقائياً" else "\n(لم تُفتح صفقة: $why)"
            }
            if (st.notifySignals) Notifier.send(ctx, Notifier.CH_SIGNALS, key.hashCode(),
                "${if (sig.side == "BUY") "🟢 شراء" else "🔴 بيع"} ${sig.symbol} — قوة ${sig.score}/100",
                signalText(sig, units) + note)
        }

        // 3) تنبيه الأخبار القوية القادمة خلال ساعة للعملات المتابعة
        if (st.notifyNews) {
            val curs = st.symbols.flatMap { listOf(Symbols.base(it), Symbols.quote(it)) }.toSet()
            for (e in news.upcoming(now, 1.0, 3)) {
                if (e.currency !in curs || e.time < now) continue
                if (store.alreadyNotified("ev:${e.currency}:${e.time}:${e.title}")) continue
                val mins = (e.time - now) / 60
                Notifier.send(ctx, Notifier.CH_NEWS, (e.title + e.time).hashCode(),
                    "🔥 خبر قوي بعد $mins دقيقة: ${e.currency}",
                    "${e.title}\nالمتوقع: ${e.forecast.ifBlank { "-" }}  السابق: ${e.previous.ifBlank { "-" }}\nتجنّب فتح صفقات على ${e.currency} قبل وبعد الخبر.")
            }
        }

        store.book = book
        store.lastRun = now
        return CycleResult(items, news, book, now)
    }
}
