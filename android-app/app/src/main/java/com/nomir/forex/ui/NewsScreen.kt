package com.nomir.forex.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nomir.forex.UiState
import com.nomir.forex.core.EconomicEvent
import com.nomir.forex.core.Symbols

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun NewsScreen(state: UiState) {
    var sub by rememberSaveable { mutableIntStateOf(0) }
    val now = System.currentTimeMillis() / 1000
    val ctx = LocalContext.current
    Column {
        TabRow(selectedTabIndex = sub) {
            Tab(sub == 0, { sub = 0 }, text = { Text("التقويم الاقتصادي") })
            Tab(sub == 1, { sub = 1 }, text = { Text("عناوين الأخبار") })
        }
        LazyColumn(Modifier.fillMaxWidth()) {
            item {
                val curs = state.settings.symbols.flatMap { listOf(Symbols.base(it), Symbols.quote(it)) }.distinct()
                SectionCard {
                    Text("اتجاه الأخبار لكل عملة (آخر 12 ساعة)", fontWeight = FontWeight.Bold)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        curs.forEach { c ->
                            val s = state.news.sentiment(c, now)
                            Chip("$c ${if (s > 0) "+$s ▲" else if (s < 0) "$s ▼" else "محايد"}",
                                if (s > 0) Buy else if (s < 0) Sell else MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
            if (sub == 0) {
                val ev = state.news.upcoming(now, 72.0, 2)
                if (ev.isEmpty()) item { SectionCard { Text(if (state.loading) "جارٍ التحميل…" else "لا توجد أحداث مهمة قادمة (أو تعذّر الجلب).") } }
                items(ev) { EventRow(it, now) }
            } else {
                val hs = state.news.headlines
                if (hs.isEmpty()) item { SectionCard { Text(if (state.loading) "جارٍ التحميل…" else "لا توجد عناوين (أو تعذّر الجلب).") } }
                items(hs.take(80)) { h ->
                    SectionCard(Modifier.clickable(enabled = h.link.isNotBlank()) {
                        runCatching { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(h.link))) }
                    }) {
                        Text(h.title, fontSize = 14.sp)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            h.time?.let { Text(fmtDate(it), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            Spacer(Modifier.weight(1f))
                            h.scores.forEach { (c, v) -> Chip("$c ${if (v > 0) "▲" else "▼"}", if (v > 0) Buy else Sell); Spacer(Modifier.width(4.dp)) }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EventRow(e: EconomicEvent, now: Long) {
    val high = e.rank >= 3
    SectionCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Chip(if (high) "🔥 قوي" else "⚠️ متوسط", if (high) Sell else Gold)
            Spacer(Modifier.width(8.dp))
            Text(e.currency, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            Text(fmtTime(e.time), fontSize = 13.sp,
                color = if (e.time < now) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary)
        }
        Text(e.title, fontSize = 14.sp)
        val parts = listOfNotNull(
            e.actual.takeIf { it.isNotBlank() }?.let { "الفعلي: $it" },
            e.forecast.takeIf { it.isNotBlank() }?.let { "المتوقع: $it" },
            e.previous.takeIf { it.isNotBlank() }?.let { "السابق: $it" })
        if (parts.isNotEmpty()) Text(parts.joinToString("   "), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
