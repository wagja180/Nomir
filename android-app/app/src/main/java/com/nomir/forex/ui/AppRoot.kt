package com.nomir.forex.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import com.nomir.forex.MainViewModel

private data class Tab(val title: String, val icon: ImageVector)

private val TABS = listOf(
    Tab("الفرص", Icons.Filled.Star),
    Tab("الأخبار", Icons.Filled.Info),
    Tab("الصفقات", Icons.Filled.List),
    Tab("الإعدادات", Icons.Filled.Settings),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppRoot(vm: MainViewModel) {
    val state by vm.state.collectAsState()
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val snack = remember { SnackbarHostState() }

    LaunchedEffect(state.message) {
        state.message?.let { snack.showSnackbar(it); vm.clearMessage() }
    }

    ForexTheme {
        CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
            Scaffold(
                topBar = {
                    TopAppBar(
                        title = { Text("نومير فوركس — ${TABS[tab].title}") },
                        actions = {
                            if (state.loading) CircularProgressIndicator(Modifier.padding(12.dp).padding(end = 4.dp))
                            else IconButton(onClick = vm::refresh) { Icon(Icons.Filled.Refresh, "تحديث") }
                        })
                },
                bottomBar = {
                    NavigationBar {
                        TABS.forEachIndexed { i, t ->
                            NavigationBarItem(selected = tab == i, onClick = { tab = i },
                                icon = { Icon(t.icon, t.title) }, label = { Text(t.title) })
                        }
                    }
                },
                snackbarHost = { SnackbarHost(snack) },
            ) { pad ->
                Box(Modifier.padding(pad)) {
                    when (tab) {
                        0 -> OpportunitiesScreen(state, vm::openTrade)
                        1 -> NewsScreen(state)
                        2 -> TradesScreen(state, vm::closeTrade, vm::resetBook)
                        else -> SettingsScreen(state.settings, vm::saveSettings)
                    }
                }
            }
        }
    }
}
