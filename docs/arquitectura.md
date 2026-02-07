# Arquitectura — RIOSAC Reporterí­a

## Objetivo
Automatizar ETAdirect (Claro Ecuador) para exportar datos operativos y generar reportes a Excel bajo demanda desde una app de escritorio.

## Componentes
### UI (CustomTkinter) — `ui/`
- Presenta filtros y botones (Actualizar Capa A/B/C, Generar reportes).
- Muestra logs/estado.
- **No contiene** lógica de Playwright ni procesamiento de datos.

### Core (Backend) — `core/`
- Playwright: login, navegación, exportaciones, extracción por actividad.
- Procesamiento por capas: limpieza, normalización, catálogos, mapeos.
- Storage: guardado diario (raw/clean/daily) y masters mensuales (parquet).
- Motor de reportes: carga masters por rango, cruces por `id_actividad`, export a Excel.

## Organización por capas
Cada capa vive en `core/layers/<capa_x>/` y produce:
- Evidencia diaria (CSV/Parquet según corresponda).
- Master mensual por capa (Parquet) para consultas rápidas.

## Regla de unión
La llave común entre capas es `id_actividad`.

## Flujo general
1) UI solicita actualización de una capa con rango/selecciones.
2) Core ejecuta:
   - (si aplica) Automatización Playwright para obtener datos
   - Procesamiento por capa
   - Guardado diario
   - Actualización master mensual
3) UI refleja logs/estado.

## Logging
- Logger central: `core/config/logging_config.py`
- Archivo: `logs/app.log`
- Consola: INFO
- Archivo: DEBUG (en `APP_ENV=dev`)