# Conexión LAN y Estructura del QR

Para que la App Móvil pueda desbloquear la PC automáticamente sin que el usuario tenga que escribir el código OTP, existe un flujo de conexión directa vía LAN (WiFi).

## 1. Estructura del Código QR

Cuando la PC muestra el código QR de "Bloqueo de Hardware", este contiene un JSON con la siguiente información:

```json
{
  "pairing_id": "a1b2c3d4e5f6...",       // ID único de la sesión de desbloqueo
  "fingerprint": "PC_NAME|WIN|X64|...",  // Huella digital de la PC bloqueada
  "server_url": "http://192.168.1.15:8000" // Dirección IP y puerto del servidor local de la PC
}
```

*   **pairing_id**: Identificador que la PC espera recibir de vuelta.
*   **server_url**: La dirección a la que la App Móvil debe intentar conectarse.

## 2. Flujo de Conexión (App Móvil)

Cuando la App Móvil escanea este QR, debe hacer lo siguiente:

1.  **Calcular el OTP**: Usar el `fingerprint` del QR para generar el código de 4 dígitos (ver `3_Bloqueo_Hardware.md`).
2.  **Intentar Conexión LAN**: Hacer una petición HTTP POST a la `server_url` del QR.

### Endpoint: Confirmar Emparejamiento

**POST** `http://{IP_PC}:8000/guardian/pair/confirm`

**Body (JSON):**
```json
{
  "pairing_id": "a1b2c3d4e5f6...", // El mismo ID del QR
  "otp": "1234"                   // El código calculado por la App
}
```

**Respuesta Esperada (200 OK):**
```json
{
  "success": true,
  "fingerprint": "..." // Confirmación de la huella registrada
}
```

### Endpoint: Confirmar Recuperación de Contraseña

Si es el flujo de "Olvidé mi contraseña", el QR tendrá un formato similar pero apuntará a este otro endpoint:

**POST** `http://{IP_PC}:8000/guardian/recover/confirm`

**Body (JSON):**
```json
{
  "challenge": "ABCD",   // El reto mostrado en pantalla
  "response": "XY1234"   // La respuesta calculada por la App
}
```

## 3. Notas Técnicas

*   **Puerto**: Por defecto la PC escucha en el puerto `8000`.
*   **Red**: Ambos dispositivos (PC y Celular) deben estar en la misma red WiFi.
*   **USB Tethering**: Si no hay WiFi, se puede conectar el celular por USB y activar "Compartir conexión por USB". La PC detectará la IP del celular y viceversa.
