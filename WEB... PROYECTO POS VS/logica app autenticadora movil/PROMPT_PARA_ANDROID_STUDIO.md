# Prompt para Crear la App Autenticadora (Android/Kotlin)

**Rol:** Eres un Desarrollador Android Senior experto en Seguridad, Criptografía y Jetpack Compose.

**Objetivo:** Crear una aplicación nativa en Android (Kotlin + Gradle) llamada **"PablitoPOS Authenticator"**. Esta app servirá como llave maestra y herramienta de verificación para un sistema de Punto de Venta de escritorio.

**Stack Tecnológico:**
*   Lenguaje: Kotlin
*   UI: Jetpack Compose (Material 3)
*   Build: Gradle (Kotlin DSL)
*   Cámara/QR: CameraX + ML Kit Barcode Scanning
*   Networking: Retrofit + OkHttp
*   Arquitectura: MVVM + Clean Architecture

---

## 1. Configuración de Seguridad (Hardcoded)
La app debe contener estas dos constantes secretas que coinciden con el software de escritorio:
```kotlin
const val SEMILLA_SECRETA = "BIOBOL_CLAVE_SECRETA_2025"
const val MASTER_SECRET = "PABLITO_MASTER_SECRET_V1"
```

## 2. Funcionalidades Principales

### A. Escáner de QR Inteligente (Pantalla Principal)
*   La app debe abrirse directamente con una cámara o un botón grande para escanear.
*   Al detectar un QR, debe identificar automáticamente qué tipo de acción es basándose en el contenido (JSON o Texto).

### B. Módulo: Recuperación de Contraseña (Challenge-Response)
*   **Input:** Un código "RETO" de 4 caracteres (ej: `X7Z2`). Puede venir de un QR o ingreso manual.
*   **Lógica:**
    1.  Concatenar: `RETO + SEMILLA_SECRETA`
    2.  Hash: `SHA-256`
    3.  Resultado: Primeros 6 caracteres del HexString en mayúsculas.
*   **Acción Automática (LAN):** Si el QR contiene una `server_url`, hacer un POST a `/guardian/recover/confirm` con `{ "challenge": "...", "response": "..." }`.

### C. Módulo: Desbloqueo de Hardware (Storage Guardian)
*   **Input:** Un JSON desde QR con `{ "pairing_id": "...", "fingerprint": "...", "server_url": "..." }`.
*   **Lógica:**
    1.  Concatenar: `FINGERPRINT + "|" + MASTER_SECRET + "|AUTHV1"`
    2.  Hash: `SHA-256`
    3.  Resultado: Primeros 4 caracteres del HexString (OTP).
*   **Acción Automática (LAN):** Hacer un POST a `/guardian/pair/confirm` con `{ "pairing_id": "...", "otp": "..." }`.
*   **Feedback:** Mostrar el OTP en pantalla grande por si falla la conexión LAN.

### D. Módulo: Verificación de Boletas
*   **Input:** Un string de texto separado por pipes `|` (desde el QR de la boleta impresa).
    *   Formato: `SERIE|NUMERO|TOTAL|FECHA|DNI|ITEMS_RESUMEN|FIRMA_IMPRESA`
*   **Lógica:**
    1.  Extraer la `FIRMA_IMPRESA` (último campo).
    2.  Reconstruir la cadena de datos original (sin la firma).
    3.  Concatenar: `DATOS + "|" + SEMILLA_SECRETA`
    4.  Hash: `SHA-256`
    5.  Tomar primeros 8 caracteres.
*   **Resultado:**
    *   Si `CALCULADO == FIRMA_IMPRESA` -> ✅ **BOLETA VÁLIDA** (Mostrar en Verde).
    *   Si no coinciden -> ❌ **BOLETA ADULTERADA** (Mostrar en Rojo y alertar).

## 3. Requisitos de UI/UX
*   **Tema:** Oscuro, estilo "Cyberpunk" o "Hacker" (Negro, Verde Neón, Gris Oscuro).
*   **Feedback:** Vibración al escanear correctamente.
*   **Navegación:** Barra inferior con: [Escanear], [Manual], [Historial].

## 4. Entregables
*   Estructura del proyecto Android Studio.
*   Código de las clases de utilidad para Criptografía (CryptoUtils.kt).
*   Código del ViewModel para manejar la lógica de escaneo y red.
*   Implementación de la UI en Compose.
*   Configuración del Manifiesto (Permisos de Cámara e Internet).

---
**Nota para el Agente:** Por favor, prioriza la exactitud de los algoritmos SHA-256 y el manejo de strings, ya que cualquier diferencia de un caracter hará que falle la autenticación con el sistema de escritorio.
