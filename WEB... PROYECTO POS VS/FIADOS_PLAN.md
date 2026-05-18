# Plan de implementacion de Fiados

## Objetivo
Agregar flujo de fiados (vale pendiente) con registro de deuda, cobro parcial con tildes por bloque, PDF con estado pendiente/tachados y cierre automatico a boleta formal cuando se paga al 100%.

## Fases
1) Esquema y capa de datos
- Migracion: tablas `fiados` y `fiado_items` (codigo C-001, cliente, estado, totales, pdf_path, sale_id opcional).
- Repositorio/servicio: crear fiado, listar por cliente, marcar item pagado/pendiente, recalcular totales y estado, guardar pdf_path.

2) PDF de vale pendiente
- Plantilla: encabezado "Vale de Fiado / Pago Pendiente", sello rojo, totales pagado/pendiente, items pagados con tachado.
- Render incremental sobre mismo pdf_path al actualizar estados.

3) UI Registro de Fiado
- Form similar a ventas: elegir cliente, agregar items, guardar como fiado (no resta stock).
- Genera PDF inicial y abre vista/toast.

4) UI Cobro (Cuaderno digital)
- Nueva vista "Fiados" en barra (configurable): buscador cliente, tarjetas por bloque (franjas grises), checkboxes por item.
- Al chequear: guarda estado, recalcula totales, re-render PDF, muestra pendiente.

5) Cierre automatico a boleta
- Si 100% pagado y no cerrada: genera boleta formal (usa SaleService), asocia sale_id y deja vale como "pagado".
- Boton manual "Generar boleta" cuando todo pagado (y reversible solo antes de generar).

## Notas de negocio
- Estados: pendiente | pagado | anulado. Items: pendiente | pagado.
- Agrupacion por bloque textual (ej. Manana/Tarde) a nivel de item.
- Dashboard y ventas existentes no se afectan; ventas de fiado se crean solo al cierre.

## Checklist inicial (Fase 1)
- [x] Backup previo.
- [ ] Migracion DB y repos/servicio fiados.
- [ ] Wire en app para tener servicio instanciado.
