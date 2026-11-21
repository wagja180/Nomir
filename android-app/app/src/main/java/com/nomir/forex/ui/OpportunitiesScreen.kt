package com.nomir.forex.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nomir.forex.UiState
import com.nomir.forex.core.ScanItem
import com.nomir.forex.core.Signal
import com.nomir.forex.core.Symbols
import java.util.Locale

@Composable
fun OpportunitiesScreen(state: UiState, onTrade: (Signal) -> Unit) {
    val signals = state.items.mapNotNull { it.state?.signal }.sortedByDescending { it.score }
    LazyColumn(Modifier.fillMaxWidth()) {
        item {
            SectionCard {
                KeyValue("الرصيد التجريبي", money(state.book.balance))
                KeyValue("صفقات مفتوحة", "${state.book.open.size} / ${state.settings.maxOpen}")
                KeyValue("الإطار الزمني", state.settings.timeframe.label)
                KeyValue("آخر تحديث", if (state.lastUpdate > 0) fmtDate(state.lastUpdate) else "—")
            }
        }
        item { SectionTitle("🎯 الفرص الحالية (${signals.size})") }
        if (signals.isEmpty()) item {
            SectionCard {
                Text(if (state.loading) "جارٍ فحص السوق…"
                     else "لا توجد فرص مطابقة للشروط الآن. البوت يفحص السوق تلقائياً ويرسل لك تنبيهاً عند ظهور فرصة.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        items(signals, key = { "s" + it.symbol + it.time }) { SignalCard(it, onTrade) }
        item { SectionTitle("📊 حالة السوق") }
        items(state.items, key = { "m" + it.symbol }) { MarketRow(it) }
        item {
            Text("⚠️ لا يوجد ربح مضمون. الإشارات احتمالية وليست نصيحة مالية — جرّب على الحساب التجريبي أولاً.",
                fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(16.dp))
        }
    }
}

@Composable
fun SignalCard(s: Signal, onTrade: (Signal) -> Unit) {
    val buy = s.side == "BUY"
    val col = if (buy) Buy else Sell
    val pip = Symbols.pip(s.symbol)
    SectionCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(s.symbol, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Spacer(Modifier.width(8.dp))
            Chip(if (buy) "شراء ▲" else "بيع ▼", col)
            Spacer(Modifier.weight(1f))
            Text("${s.score}/100", fontWeight = FontWeight.Bold, color = col)
        }
        LinearProgressIndicator(progress = { s.score / 100f }, color = col, modifier = Modifier.fillMaxWidth())
        KeyValue("الدخول", Symbols.fmt(s.symbol, s.entry))
        KeyValue("وقف الخسارة", "${Symbols.fmt(s.symbol, s.stopLoss)}  (${(Math.abs(s.entry - s.stopLoss) / pip).toInt()} نقطة)", Sell)
        KeyValue("جني الربح", "${Symbols.fmt(s.symbol, s.takeProfit)}  (${(Math.abs(s.takeProfit - s.entry) / pip).toInt()} نقطة)", Buy)
        KeyValue("العائد / المخاطرة", String.format(Locale.US, "1 : %.1f", s.riskReward))
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            s.reasons.forEach { Text("• $it", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        Text("وقت الإشارة: ${fmtDate(s.time)}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = { onTrade(s) }, modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = col)) { Text("فتح صفقة تجريبية") }
    }
}

@Composable
fun MarketRow(it: ScanItem) {
    SectionCard {
        val st = it.state
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(it.symbol, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Spacer(Modifier.width(8.dp))
            when {
                it.error != null -> Chip("خطأ", Sell)
                st == null -> Chip("بيانات غير كافية", MaterialTheme.colorScheme.onSurfaceVariant)
                st.trend > 0 -> Chip("صاعد", Buy)
                st.trend < 0 -> Chip("هابط", Sell)
                else -> Chip("عرضي", Gold)
            }
            Spacer(Modifier.weight(1f))
            if (st != null) Column(horizontalAlignment = Alignment.End) {
                Text(Symbols.fmt(it.symbol, st.price), fontWeight = FontWeight.SemiBold)
                Text(String.format(Locale.US, "%+.2f%%", st.changePct), fontSize = 12.sp,
                    color = if (st.changePct >= 0) Buy else Sell)
            }
        }
        if (st != null) Text(String.format(Locale.US, "RSI %.0f   •   ADX %.0f", st.rsi, st.adx),
            fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        it.blockedBy?.let { e -> Text("⏸️ متوقف مؤقتاً: خبر قوي ${e.currency} — ${e.title} (${fmtTime(e.time)})",
            fontSize = 12.sp, color = Gold) }
        it.error?.let { e -> Text(e, fontSize = 12.sp, color = Sell) }
    }
}
