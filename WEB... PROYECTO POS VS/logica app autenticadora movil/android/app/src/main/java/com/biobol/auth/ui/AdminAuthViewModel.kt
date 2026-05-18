package com.biobol.auth.ui

import androidx.compose.runtime.MutableState
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import com.biobol.auth.security.SecurityUtils

class AdminAuthViewModel : ViewModel() {
    private val _reto: MutableState<String> = mutableStateOf(SecurityUtils.generarReto())
    val reto: MutableState<String> = _reto
    val isValid: MutableState<Boolean> = mutableStateOf(false)

    fun validar(respuesta: String) {
        val ok = SecurityUtils.verificarRespuesta(_reto.value, respuesta)
        isValid.value = ok
        if (!ok) {
            _reto.value = SecurityUtils.generarReto()
        }
    }
}
