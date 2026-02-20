from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


_COL_EQUIV = {
    "id_actividad": [
        "id actividad",
        "id de actividad",
        "id_actividad",
        "activity id",
        "activity_id",
        "id",
    ],
    "orden_trabajo": [
        "orden de trabajo",
        "orden trabajo",
        "orden",
        "ot",
        "work order",
        "work_order",
        "wo",
    ],
    "fecha": [
        "fecha",
        "fecha de actividad",
        "fecha actividad",
        "date",
        "activity date",
        "fecha de ejecución",
        "fecha de despacho",
    ],
}


@dataclass(frozen=True)
class QueueBuildResult:
    month: str
    total_ids: int
    output_path: Path


def _normalize_colname(value: str) -> str:
    return (value or "").strip().lower().replace("\ufeff", "")


def _find_column(df: pd.DataFrame, logical_name: str) -> Optional[str]:
    candidates = _COL_EQUIV.get(logical_name, [])
    normalized = {_normalize_colname(col): col for col in df.columns}
    for candidate in candidates:
        cand_norm = _normalize_colname(candidate)
        if cand_norm in normalized:
            return normalized[cand_norm]
    return None


def _load_master_df(masters_root: Path, month: str) -> pd.DataFrame:
    master_path = masters_root / "capa_b" / f"capa_b_actividades_{month}.parquet"
    if not master_path.exists():
        raise FileNotFoundError(f"No existe el master parquet para el mes {month}: {master_path}")
    return pd.read_parquet(master_path)


def _read_existing_queue(path: Path) -> dict[str, object]:
    if not path.exists():  # pragma: no cover - defensive
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generate_ids_queue(
    *,
    month: str,
    masters_root: Path,
    overwrite: bool = False,
    logger=None,
) -> QueueBuildResult:
    out_dir = masters_root / "capa_c"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"queue_ids_{month}.json"

    if out_path.exists() and not overwrite:
        existing = _read_existing_queue(out_path)
        if logger:
            logger.info("Queue ya existe (skip): %s", out_path)
        total = int(existing.get("total_ids", 0)) if existing else 0
        return QueueBuildResult(month=month, total_ids=total, output_path=out_path)

    df = _load_master_df(masters_root, month)

    col_order = _find_column(df, "orden_trabajo")
    if not col_order:
        raise ValueError("No se encontró columna equivalente a 'Orden de trabajo' en el master.")

    col_fecha = _find_column(df, "fecha")

    working = df.copy()
    if col_fecha:
        parsed = pd.to_datetime(working[col_fecha], errors="coerce", dayfirst=True)
        working["__fecha_sort"] = parsed
    working["__row_index"] = range(len(working))

    sort_keys: list[str] = []
    if col_fecha:
        sort_keys.append("__fecha_sort")
    sort_keys.append("__row_index")
    working = working.sort_values(by=sort_keys, kind="stable")

    order_series = working[col_order].astype(str).str.strip()
    order_series = order_series[order_series != ""]
    unique_ids = order_series.drop_duplicates().tolist()

    payload = {
        "month": month,
        "total_ids": len(unique_ids),
        "ids": unique_ids,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if logger:
        logger.info(
            "Queue generada: month=%s total_ids=%s output=%s",
            month,
            len(unique_ids),
            out_path,
        )

    return QueueBuildResult(month=month, total_ids=len(unique_ids), output_path=out_path)
