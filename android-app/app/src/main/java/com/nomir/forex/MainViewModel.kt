package com.nomir.forex

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.nomir.forex.core.NewsState
import com.nomir.forex.core.PaperBook
import com.nomir.forex.core.Position
import com.nomir.forex.core.ScanItem
import com.nomir.forex.core.Settings
import com.nomir.forex.core.Signal
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class UiState(
    val loading: Boolean = false,
    val items: List<ScanItem> = emptyList(),
    val news: NewsState = NewsState(emptyList(), emptyList()),
    val book: PaperBook = PaperBook(),
    val settings: Settings = Settings(),
    val lastUpdate: Long = 0,
    val message: String? = null,
)

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val store = Store(app)
    private val _state = MutableStateFlow(UiState(book = store.book, settings = store.settings, lastUpdate = store.lastRun))
    val state: StateFlow<UiState> = _state

    init { refresh() }

    fun refresh() {
        if (_state.value.loading) return
        _state.update { it.copy(loading = true, message = null) }
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val r = Engine.cycle(getApplication(), background = false)
                val errors = r.items.count { it.error != null }
                _state.update {
                    it.copy(loading = false, items = r.items, news = r.news, book = store.book, lastUpdate = r.time,
                        message = when {
                            errors == r.items.size && errors > 0 -> "تعذّر جلب الأسعار — تحقق من الإنترنت"
                            r.news.events.isEmpty() -> "تعذّر جلب التقويم الاقتصادي"
                            else -> null
                        })
                }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, message = "خطأ: ${e.message}") }
            }
        }
    }

    fun openTrade(sig: Signal) {
        val book = store.book
        val (pos, why) = Engine.tryOpen(store, book, sig, _state.value.items, System.currentTimeMillis() / 1000)
        if (pos != null) store.book = book
        _state.update { it.copy(book = store.book, message = if (pos != null) "تم فتح صفقة تجريبية ${pos.symbol}" else why) }
    }

    fun closeTrade(p: Position) {
        val book = store.book
        val target = book.open.firstOrNull { it.id == p.id } ?: return
        val items = _state.value.items
        val price = items.firstOrNull { it.symbol == p.symbol }?.state?.price ?: return
        book.close(target, price, "إغلاق يدوي", System.currentTimeMillis() / 1000, Engine.q2a(p.symbol, price, items))
        store.book = book
        _state.update { it.copy(book = store.book) }
    }

    fun resetBook() {
        val b = store.book.apply { reset(store.settings.startBalance) }
        store.book = b
        _state.update { it.copy(book = store.book, message = "تمت إعادة تعيين الحساب التجريبي") }
    }

    fun saveSettings(s: Settings) {
        store.settings = s
        ScanWorker.schedule(getApplication(), s.intervalMin)
        _state.update { it.copy(settings = s, message = "تم حفظ الإعدادات") }
        refresh()
    }

    fun clearMessage() = _state.update { it.copy(message = null) }
}
