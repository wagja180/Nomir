package com.nomir.forex.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.nomir.forex.Engine
import com.nomir.forex.UiState
import com.nomir.forex.core.Position
import com.nomir.forex.core.Symbols
import java.util.Locale

@Composable
fun TradesScreen(state: UiState, onClose: (Position) -> Unit, onReset: () -> Unit) {
    val book = state.book
    val prices = Engine.prices(state.items)
    val floating = book.open.sumOf { p -> prices[p.symbol]?.let { p.floating(it, Engine.q2a(p.symbol, it, state.items)) } ?: 0.0 }
    var confirm by remember { mutableStateOf(false) }

    LazyColumn(Modifier.fillMaxWidth()) {
        item {
            SectionCard {
                Text("الحساب التجريبي", fontWeight = FontWeight.Bold)
                KeyValue("الرصيد", money(book.balance))
                KeyValue("الربح/الخسارة العائم", signed(floating), pnlColor(floating))
                val total = book.balance - state.settings.startBalance
                KeyValue("إجمالي الربح/الخسارة المحقق", signed(total), pnlColor(total))
                KeyValue("عدد الصفقات المغلقة", book.history.size.toString())
                KeyValue("نسبة الصفقات الرابحة", String.format(Locale.US, "%.0f%%", book.winRate()))
                OutlinedButton(onClick = { confirm = true }, modifier = Modifier.fillMaxWidth()) { Text("إعادة تعيين الحساب") }
            }
        }
        item { SectionTitle("الصفقات المفتوحة (${book.open.size})") }
        if (book.open.isEmpty()) item { SectionCard { Text("لا توجد صفقات مفتوحة", color = MaterialTheme.colorScheme.onSurfaceVariant) } }
        items(book.open, key = { "o" + it.id }) { p ->
            val px = prices[p.symbol]
            val fl = px?.let { p.floating(it, Engine.q2a(p.symbol, it, state.items)) }
            SectionCard {
                Header(p)
                KeyValue("الدخول", Symbols.fmt(p.symbol, p.entry))
                KeyValue("السعر الحالي", px?.let { Symbols.fmt(p.symbol, it) } ?: "—")
                KeyValue("الوقف / الهدف", "${Symbols.fmt(p.symbol, p.stopLoss)} / ${Symbols.fmt(p.symbol, p.takeProfit)}")
                KeyValue("الحجم", String.format(Locale.US, "%,d وحدة (%.2f لوت)", p.units, p.units / 100000.0))
                KeyValue("الربح/الخسارة", fl?.let { signed(it) } ?: "—", pnlColor(fl ?: 0.0))
                OutlinedButton(onClick = { onClose(p) }, enabled = px != null, modifier = Modifier.fillMaxWidth()) {
                    Text("إغلاق الصفقة الآن")
                }
            }
        }
        item { SectionTitle("السجل") }
        items(book.history.take(100), key = { "h" + it.id }) { p ->
            SectionCard {
                Header(p)
                KeyValue("${Symbols.fmt(p.symbol, p.entry)} ← ${p.exit?.let { Symbols.fmt(p.symbol, it) } ?: "—"}",
                    signed(p.pnl), pnlColor(p.pnl))
                Text("${p.reason} • ${p.closedAt?.let { fmtDate(it) } ?: ""}", fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }

    if (confirm) AlertDialog(
        onDismissRequest = { confirm = false },
        confirmButton = { TextButton(onClick = { confirm = false; onReset() }) { Text("نعم، أعد التعيين") } },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text("إلغاء") } },
        title = { Text("إعادة تعيين الحساب التجريبي؟") },
        text = { Text("سيتم حذف كل الصفقات وإرجاع الرصيد إلى ${money(state.settings.startBalance)}.") },
    )
}

@Composable
private fun Header(p: Position) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(p.symbol, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Spacer(Modifier.width(8.dp))
        Chip(if (p.side == "BUY") "شراء" else "بيع", if (p.side == "BUY") Buy else Sell)
        Spacer(Modifier.weight(1f))
        Text(fmtDate(p.openedAt), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
