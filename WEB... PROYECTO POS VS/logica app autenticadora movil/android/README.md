# Biobol Auth (Kotlin)

Estructura lista para Android Studio con Compose y la logica migrada desde Python.

## Modulos
- app/src/main/java/com/biobol/auth/security/SecurityUtils.kt: utilidades de reto, firma de boleta, huella y codigo de emergencia.
- app/src/main/java/com/biobol/auth/ui/AdminAuthViewModel.kt: ViewModel para challenge-response.
- app/src/main/java/com/biobol/auth/ui/AdminRecoveryScreen.kt: pantalla Compose con estilo neon.
- app/src/main/java/com/biobol/auth/ui/theme/Theme.kt: paleta cyberpunk y helpers de estilo.
- app/src/main/java/com/biobol/auth/MainActivity.kt: host Compose.

## Notas de seguridad
- Mantener las constantes secretas fuera de logs; considerar NDK o EncryptedSharedPreferences.
- En Android usar Build.MODEL/DEVICE, Build.VERSION y Settings.Secure.ANDROID_ID para alimentar huella; evitar MAC por randomizacion.

## Como abrir
1. Abrir carpeta `android` en Android Studio.
2. Sincronizar Gradle (usa Kotlin 1.9.22 y Compose 1.5.x BOM 2024.02.00).
3. Ejecutar app; la pantalla inicial muestra el flujo de reto/respuesta.
