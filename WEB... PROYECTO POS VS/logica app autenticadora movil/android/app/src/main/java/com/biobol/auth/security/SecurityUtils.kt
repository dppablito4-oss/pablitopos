package com.biobol.auth.security

import java.security.MessageDigest
import java.util.Locale

object SecurityUtils {
    private const val SEMILLA_SECRETA = "BIOBOL_CLAVE_SECRETA_2025"
    private const val MASTER_SECRET = "PABLITO_MASTER_SECRET_V1"
    private val CHALLENGE_ALPHABET = ('A'..'Z') + ('0'..'9')

    fun generarReto(length: Int = 4): String =
        (1..length).joinToString("") { CHALLENGE_ALPHABET.random().toString() }

    fun verificarRespuesta(retoMostrado: String, respuestaIngresada: String): Boolean {
        val payload = "${retoMostrado.trim().uppercase(Locale.US)}$SEMILLA_SECRETA"
        val esperado = sha256(payload).take(6)
        return respuestaIngresada.trim().uppercase(Locale.US) == esperado
    }

    fun generarFirmaBoleta(
        serie: String,
        numero: String,
        total: Double,
        fechaHora: String,
        dniCliente: String,
        itemsResumen: String
    ): String {
        val itemsSafe = itemsResumen.replace("|", "-")
        val data = listOf(
            serie.trim().uppercase(Locale.US),
            numero.trim().uppercase(Locale.US),
            String.format(Locale.US, "%.2f", total),
            fechaHora.trim(),
            dniCliente.trim().uppercase(Locale.US),
            itemsSafe,
            SEMILLA_SECRETA
        ).joinToString("|")
        return sha256(data).take(8)
    }

    fun obtenerHuellaHardware(
        deviceName: String,
        osVersion: String,
        abi: String,
        androidId: String
    ): String {
        val raw = "$deviceName|$osVersion|$abi|$androidId"
        return sha256(raw)
    }

    fun generarCodigoEmergencia(fingerprint: String): String {
        val payload = "${fingerprint.trim().uppercase(Locale.US)}|$MASTER_SECRET|AUTHV1"
        return sha256(payload).take(4)
    }

    private fun sha256(text: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(text.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02X".format(it) }
    }
}
