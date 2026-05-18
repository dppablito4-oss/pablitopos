# Lógica de Verificación de Boleta (Firma Digital)

Este módulo asegura la integridad de los comprobantes emitidos. Cada boleta impresa o PDF lleva un "Serial de Seguridad" único.

## Objetivo
Detectar si una boleta ha sido adulterada (ej: cambiar el monto total o la fecha) después de haber sido emitida.

## Flujo de Trabajo

1.  **Emisión (Sistema POS):**
    *   Al guardar una venta, el sistema toma los datos clave: Serie, Número, Total, Fecha, DNI Cliente e Items.
    *   Genera una **FIRMA** digital única usando estos datos y la `SEMILLA_SECRETA`.
    *   Guarda esta firma en la base de datos y la imprime en el comprobante (y en el QR).

2.  **Verificación (App Móvil):**
    *   El usuario escanea el QR de la boleta o ingresa los datos manualmente.
    *   La App Móvil vuelve a calcular la firma con los datos que ve.
    *   Si la firma calculada NO coincide con la impresa en el papel, significa que el documento es **FALSO** o ha sido adulterado.

## Algoritmo

```python
DATA_STRING = Serie + "|" + Numero + "|" + Total + "|" + Fecha + "|" + DNI + "|" + Items + "|" + SEMILLA_SECRETA
HASH = SHA256( DATA_STRING )
SERIAL = Primeros_8_Caracteres( HASH )
```

*   **Nota**: Los separadores `|` son importantes para evitar colisiones.
*   **Items**: Se recomienda usar un resumen o lista de IDs para no hacer la cadena muy larga.
