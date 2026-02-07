# Decisiones técnicas

## 1) JIT Columns por capa
Las columnas se definen **just-in-time**:
- Capa A: se define al ver el CSV real exportado.
- Capa B: se define al ver Info Venta real.
- Capa C: inventario tiene columnas fijas (catálogo) y mapeos.

## 2) Persistencia diaria + master mensual
- Diario: evidencia y trazabilidad (raw/clean/daily por capa).
- Mensual: performance para reportes (parquet por capa).

## 3) Reportes bajo demanda
Los reportes se generan **solo cuando el usuario lo pide** desde la UI.
La app carga masters necesarios (uno o varios meses) y cruza solo las capas requeridas:
- A solo
- A + B
- A + C

## 4) Separación core / ui
- `ui/` no importa Playwright ni hace procesamiento.
- `core/` no importa CustomTkinter.

## 5) Clave común
Todo cruce se hace por `id_actividad`.