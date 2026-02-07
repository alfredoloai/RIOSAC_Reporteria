# RIOSAC — Mini-sistema de reportería (ETAdirect Claro Ecuador)

App de escritorio (CustomTkinter) + core backend (Python) para:
- Automatizar el portal ETAdirect de Claro Ecuador con Playwright.
- Exportar CSV diarios por cuadrilla (Capa A RAW) y procesarlos por capas.
- Construir masters mensuales por capa en Parquet para reportes rápidos bajo demanda.
- Generar reportes a Excel desde la UI (sin ejecuciones automáticas de reportes).

## Arquitectura (reglas)
- **No vibecoding**: arquitectura limpia separando:
  - `core/` (backend: playwright, procesamiento, almacenamiento, reportes)
  - `ui/` (frontend: interfaz; solo llama funciones del core)
- Datos por **capas**, cada capa en archivos separados, asociadas por `id_actividad`.
- Reportes: **solo bajo demanda** desde la UI (cargando masters por mes según rango de fechas).

## Capas
- **Capa A**: export CSV + limpieza (finalizadas + OT).
- **Capa B**: Info Venta (detalle por actividad).
- **Capa C**: Info Cierre (inventario con columnas fijas; si no aplica, 0).
- Capas futuras si aparecen más secciones.

## Estructura de datos (storage)
- Por día (evidencia):
  - `data/raw/` → CSV original exportado
  - `data/clean/` → CSV filtrado/limpio (según reglas de la capa)
  - `data/daily/capa_x/` → resultados diarios por capa (B/C/etc)
- Por mes (masters para reportes):
  - `data/masters/capa_a/capa_a_actividades_YYYY-MM.parquet`
  - `data/masters/capa_b/capa_b_venta_YYYY-MM.parquet`
  - `data/masters/capa_c/capa_c_cierre_YYYY-MM.parquet`

## Requisitos
- Windows 10/11
- Python 3.12+
- Git

## Instalación
```powershell
cd D:\Proyectos\RIOSAC

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install