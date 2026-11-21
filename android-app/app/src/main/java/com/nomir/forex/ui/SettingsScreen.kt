package com.nomir.forex.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nomir.forex.core.Settings
import com.nomir.forex.core.Timeframe
import java.util.Locale

val ALL_SYMBOLS = listOf("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
    "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "XAUUSD")

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SettingsScreen(initial: Settings, onSave: (Settings) -> Unit) {
    var s by remember(initial) { mutableStateOf(initial) }
    Column(Modifier.verticalScroll(rememberScrollState())) {
        SectionCard {
            Text("الأزواج المتابعة", fontWeight = FontWeight.Bold)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                ALL_SYMBOLS.forEach { sym ->
                    FilterChip(selected = sym in s.symbols, label = { Text(sym) }, onClick = {
                        s = s.copy(symbols = if (sym in s.symbols) s.symbols - sym else s.symbols + sym)
                    })
                }
            }
            Text("الإطار الزمني", fontWeight = FontWeight.Bold)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Timeframe.entries.forEach { tf ->
                    FilterChip(selected = s.timeframe == tf, onClick = { s = s.copy(timeframe = tf) }, label = { Text(tf.label) })
                }
            }
        }
        SectionCard {
            Text("الاستراتيجية", fontWeight = FontWeight.Bold)
            SliderRow("أقل قوة للإشارة", "${s.minScore}/100", s.minScore.toFloat(), 50f..95f, 8) { s = s.copy(minScore = it.toInt()) }
            SliderRow("العائد إلى المخاطرة", String.format(Locale.US, "1:%.1f", s.rr), s.rr.toFloat(), 1f..4f, 5) { s = s.copy(rr = it.toDouble()) }
            SliderRow("وقف الخسارة (× ATR)", String.format(Locale.US, "%.1f", s.slAtrMult), s.slAtrMult.toFloat(), 1f..3f, 3) { s = s.copy(slAtrMult = it.toDouble()) }
        }
        SectionCard {
            Text("إدارة المخاطر", fontWeight = FontWeight.Bold)
            SliderRow("المخاطرة لكل صفقة", String.format(Locale.US, "%.1f%%", s.riskPct), s.riskPct.toFloat(), 0.5f..3f, 4) { s = s.copy(riskPct = it.toDouble()) }
            SliderRow("أقصى عدد صفقات مفتوحة", "${s.maxOpen}", s.maxOpen.toFloat(), 1f..8f, 6) { s = s.copy(maxOpen = it.toInt()) }
            SliderRow("حد الخسارة اليومي", String.format(Locale.US, "%.0f%%", s.maxDailyLossPct), s.maxDailyLossPct.toFloat(), 1f..10f, 8) { s = s.copy(maxDailyLossPct = it.toDouble()) }
            SliderRow("رصيد البداية التجريبي", money(s.startBalance), s.startBalance.toFloat(), 1000f..100000f, 98) { s = s.copy(startBalance = it.toDouble()) }
        }
        SectionCard {
            Text("التشغيل التلقائي والتنبيهات", fontWeight = FontWeight.Bold)
            SwitchRow("تداول تجريبي تلقائي عند ظهور إشارة", s.autoTrade) { s = s.copy(autoTrade = it) }
            SwitchRow("تنبيه عند ظهور فرصة", s.notifySignals) { s = s.copy(notifySignals = it) }
            SwitchRow("تنبيه قبل الأخبار القوية", s.notifyNews) { s = s.copy(notifyNews = it) }
            SwitchRow("إيقاف الإشارات قرب الأخبار القوية", s.newsBlackout) { s = s.copy(newsBlackout = it) }
            Text("الفحص في الخلفية كل:", fontSize = 14.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf(15, 30, 60).forEach { m ->
                    FilterChip(selected = s.intervalMin == m, onClick = { s = s.copy(intervalMin = m) }, label = { Text("$m دقيقة") })
                }
            }
        }
        Button(onClick = { onSave(s) }, enabled = s.symbols.isNotEmpty(),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp)) { Text("حفظ الإعدادات") }
        Text("التداول في الفوركس عالي المخاطر ولا يوجد ربح مضمون. هذا التطبيق يتداول بمال وهمي فقط، " +
            "والإشارات أداة مساعدة وليست نصيحة مالية. البيانات من Yahoo Finance والتقويم الاقتصادي من ForexFactory.",
            fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(16.dp))
    }
}

@Composable
private fun SliderRow(label: String, value: String, v: Float, range: ClosedFloatingPointRange<Float>, steps: Int,
                      onChange: (Float) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 14.sp); Spacer(Modifier.weight(1f)); Text(value, fontWeight = FontWeight.SemiBold)
    }
    Slider(value = v.coerceIn(range), onValueChange = onChange, valueRange = range, steps = steps)
}

@Composable
private fun SwitchRow(label: String, v: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 14.sp, modifier = Modifier.weight(1f)); Switch(checked = v, onCheckedChange = onChange)
    }
}
