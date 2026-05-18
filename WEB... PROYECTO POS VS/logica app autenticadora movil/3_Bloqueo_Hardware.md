# Lógica de Bloqueo por Hardware (Storage Guardian)

Este es el sistema de seguridad más avanzado. Encripta la base de datos para que solo funcione en **LA MISMA COMPUTADORA** donde se creó.

## Problema
Si alguien copia el archivo `boletas.sqlite3` a otra PC, podría leer toda la información de ventas y clientes.

## Solución
El sistema cifra la base de datos con una llave que depende de la "Huella Digital" del hardware (CPU, MAC Address, Nombre de PC).

## Flujo de Desbloqueo (Migración)

Si el dueño legítimo quiere mover su base de datos a una PC nueva (ej: compró una laptop nueva):

1.  **PC Nueva (Sistema POS):**
    *   Detecta que la base de datos está cifrada con una huella de hardware diferente (la de la PC vieja).
    *   Bloquea el acceso y muestra un **Código de Huella** (Fingerprint) de la nueva PC.
    *   Pide un **Código de Emergencia (OTP)**.

2.  **App Móvil (Autenticador):**
    *   El dueño (que tiene la App Móvil autorizada) ingresa a "Desbloquear PC".
    *   Escanea o ingresa el Fingerprint de la PC nueva.
    *   La App genera el **Código OTP** usando el `MASTER_SECRET`.

3.  **PC Nueva:**
    *   El usuario ingresa el OTP.
    *   El sistema verifica el OTP.
    *   Si es correcto, **RE-ENCRIPTA** la base de datos con la huella de la nueva PC.

## Algoritmo

### 1. Huella de Hardware (Fingerprint)
```python
RAW = NombrePC + "|" + SistemaOperativo + "|" + Arquitectura + "|" + MacAddress
FINGERPRINT = SHA256( RAW )
```

### 2. Código de Emergencia (OTP)
```python
PAYLOAD = FINGERPRINT + "|" + MASTER_SECRET + "|" + "AUTHV1"
HASH = SHA256( PAYLOAD )
OTP = Primeros_4_Caracteres( HASH )
```

*   **MASTER_SECRET**: `PABLITO_MASTER_SECRET_V1` (Solo conocido por la App Móvil y el código fuente compilado).
