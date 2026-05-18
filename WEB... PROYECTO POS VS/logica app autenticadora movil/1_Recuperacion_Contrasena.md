# Lógica de Recuperación de Contraseña (Challenge-Response)

Este módulo permite al administrador recuperar el acceso al sistema si olvida su PIN, utilizando la App Móvil como llave maestra.

## Flujo de Trabajo

1.  **PC (Sistema POS):**
    *   El usuario hace clic en "¿Olvidó su contraseña?".
    *   El sistema genera un **RETO** aleatorio de 4 caracteres (ej: `X7Z2`).
    *   Muestra este reto en pantalla.

2.  **App Móvil (Autenticador):**
    *   El usuario abre la función "Generar Respuesta".
    *   Ingresa el código RETO (`X7Z2`) que ve en la pantalla del PC.
    *   La App calcula internamente la **RESPUESTA** usando la `SEMILLA_SECRETA`.
    *   Muestra la respuesta de 6 caracteres (ej: `A1B2C3`).

3.  **PC (Sistema POS):**
    *   El usuario ingresa el código de respuesta (`A1B2C3`).
    *   El sistema verifica si el código coincide con su propio cálculo.
    *   Si coincide, permite resetear el PIN.

## Algoritmo

```python
HASH = SHA256( RETO + SEMILLA_SECRETA )
RESPUESTA = Primeros_6_Caracteres( HASH )
```

*   **RETO**: 4 caracteres alfanuméricos aleatorios.
*   **SEMILLA_SECRETA**: `BIOBOL_CLAVE_SECRETA_2025` (Debe estar hardcodeada en ambas apps).
