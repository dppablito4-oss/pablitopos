package com.biobol.auth.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.TextFieldColors

private val NeonTeal = Color(0xFF34FFD4)
private val NeonMagenta = Color(0xFFFF2DD5)
private val DeepNavy = Color(0xFF0A0D1A)
private val NeonAmber = Color(0xFFF7C948)

private val darkScheme = darkColorScheme(
    primary = NeonTeal,
    secondary = NeonMagenta,
    tertiary = NeonAmber,
    background = DeepNavy,
    surface = DeepNavy,
    onPrimary = DeepNavy,
    onSecondary = DeepNavy,
    onTertiary = DeepNavy,
    onBackground = NeonTeal,
    onSurface = NeonTeal
)

private val lightScheme = lightColorScheme(
    primary = NeonTeal,
    secondary = NeonMagenta,
    tertiary = NeonAmber,
    background = Color(0xFF0E1122),
    surface = Color(0xFF0E1122),
    onPrimary = DeepNavy,
    onSecondary = DeepNavy,
    onTertiary = DeepNavy,
    onBackground = NeonTeal,
    onSurface = NeonTeal
)

@Composable
fun BiobolTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) darkScheme else lightScheme
    MaterialTheme(colorScheme = colors, content = content)
}

@Composable
fun cyberTitleStyle(): TextStyle = TextStyle(
    color = NeonTeal,
    fontSize = 24.sp,
    fontWeight = FontWeight.Bold,
    fontFamily = FontFamily.Monospace
)

@Composable
fun neonCodeStyle(): TextStyle = TextStyle(
    color = NeonMagenta,
    fontSize = 20.sp,
    fontWeight = FontWeight.SemiBold,
    fontFamily = FontFamily.Monospace
)

@Composable
fun neonTextFieldColors(): TextFieldColors = TextFieldDefaults.colors(
    focusedContainerColor = DeepNavy,
    unfocusedContainerColor = DeepNavy,
    focusedIndicatorColor = NeonTeal,
    unfocusedIndicatorColor = NeonMagenta,
    cursorColor = NeonTeal,
    focusedTextColor = NeonTeal,
    unfocusedTextColor = NeonTeal,
    focusedLabelColor = NeonTeal,
    unfocusedLabelColor = NeonMagenta
)
