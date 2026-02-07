from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

COL_ESTADO = "estado_actividad"
COL_OT = "orden_trabajo"
COLS_DROP_CLEAN = [
    "Código postal",
    "Intervalo de tiempo",
    "Ventana de servicio",
    "Inicio de SLA",
    "Fin de SLA",
    "Descripción",
    "Modelo",
    "Serial",
    "Cantidad",
    "Número Pedestal",
    "Hub",
    "Nodo",
    "Puerto amplificador",
    "Puerto Tap",
    "Motivo Reagendamiento",
    "Motivo de Suspensión",
    "Motivo de No Realizada",
    "Coordenadas Inicio",
    "Coordenada X",
    "Coordenada Y",
    "Coordenadas Fin",
    "Correo IPTV/OTT",
    "Contactos Telefónicos",
]

STOPWORDS = {"de", "del", "la", "el", "los", "las"}
COLUMN_ALIASES = {
    COL_ESTADO: ["estado de actividad", "estado actividad", "status", "estado"],
    COL_OT: ["orden de trabajo", "orden trabajo", "ot", "work_order", "orden"],
}


def _normalize_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_status(value: Any) -> str:
    return _normalize_str(value).lower()


def _norm(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _drop_stopwords(value: str) -> str:
    parts = [part for part in value.split("_") if part and part not in STOPWORDS]
    return "_".join(parts)


def _resolve_column_name(columns: list[str], canonical: str) -> str | None:
    aliases = COLUMN_ALIASES.get(canonical, [])
    wanted = {_norm(canonical)} | {_norm(alias) for alias in aliases}

    normalized_index = {_norm(col): col for col in columns}
    for candidate in wanted:
        match = normalized_index.get(candidate)
        if match:
            return match

    reduced_index = {_drop_stopwords(key): original for key, original in normalized_index.items()}
    for candidate in wanted:
        reduced_candidate = _drop_stopwords(candidate)
        match = reduced_index.get(reduced_candidate)
        if match:
            return match
    return None


def _resolve_column(df: pd.DataFrame, base_name: str) -> str:
    resolved = _resolve_column_name(df.columns.tolist(), base_name)
    if resolved is None:
        raise ValueError(f"Falta columna requerida equivalente a '{base_name}'.")
    return resolved


def clean_part1(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo actividades finalizadas con orden de trabajo no vacía."""

    estado_col = _resolve_column(df, COL_ESTADO)
    ot_col = _resolve_column(df, COL_OT)

    estado = df[estado_col].astype(str).map(_normalize_status)
    ot = df[ot_col].astype(str).map(_normalize_str)

    mask = (estado == "finalizada") & (ot != "")
    cleaned = df.loc[mask].copy()
    cleaned = cleaned.drop(columns=COLS_DROP_CLEAN, errors="ignore")
    return cleaned.reset_index(drop=True)
