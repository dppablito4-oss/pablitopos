package com.biobol.auth.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardOptions
import androidx.compose.ui.unit.dp
import com.biobol.auth.ui.theme.cyberTitleStyle
import com.biobol.auth.ui.theme.neonCodeStyle
import com.biobol.auth.ui.theme.neonTextFieldColors

@Composable
fun AdminRecoveryScreen(vm: AdminAuthViewModel) {
    val reto by vm.reto
    val isValid by vm.isValid
    var respuesta = remember { mutableStateOf("") }

    val buttonColor by animateColorAsState(
        if (isValid) Color(0xFF34FFD4) else Color(0xFFFF2DD5), label = "buttonColor"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    colors = listOf(Color(0xFF0A0D1A), Color(0xFF1A103A), Color(0xFF0A0D1A))
                )
            )
            .padding(24.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(text = "Auth Console", style = cyberTitleStyle())
            Text(text = "Reto: $reto", style = neonCodeStyle())
            OutlinedTextField(
                value = respuesta.value,
                onValueChange = { respuesta.value = it },
                label = { Text("Respuesta") },
                colors = neonTextFieldColors(),
                singleLine = true,
                keyboardActions = KeyboardActions(onDone = { vm.validar(respuesta.value) }),
                keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Done)
            )
            Button(
                onClick = { vm.validar(respuesta.value) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                colors = ButtonDefaults.buttonColors(containerColor = buttonColor)
            ) {
                Text(text = "Validar", color = Color(0xFF0A0D1A))
            }
            if (isValid) {
                Text(text = "Acceso concedido", color = Color(0xFF34FFD4))
            }
        }
    }
}
