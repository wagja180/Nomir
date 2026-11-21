package com.nomir.forex.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Buy = Color(0xFF1E9E5A)
val Sell = Color(0xFFD64545)
val Gold = Color(0xFFE0A526)

private val Dark = darkColorScheme(
    primary = Color(0xFF4FC3F7), onPrimary = Color(0xFF00253A),
    secondary = Gold, background = Color(0xFF0D1520), surface = Color(0xFF131E2B),
    surfaceVariant = Color(0xFF1C2A3A), onSurface = Color(0xFFE6EDF5), onSurfaceVariant = Color(0xFF9FB0C3),
)
private val Light = lightColorScheme(
    primary = Color(0xFF0B6FA4), secondary = Color(0xFFB07A00),
    background = Color(0xFFF3F6FA), surface = Color.White, surfaceVariant = Color(0xFFE6ECF3),
)

@Composable
fun ForexTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}
