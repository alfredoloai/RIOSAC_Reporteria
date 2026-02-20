from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


_COL_EQUIV = {
    "id_actividad": [
        "id_actividad",
        "id actividad",
        "id de actividad",
        "activity id",
        "activity_id",
        "id",
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
class MasterBuildResult:
    month: str
    input_files: int
    rows: int
    output_path: Path


def _normalize_colname(s: str) -> str:
    return (s or "").strip().lower().replace("\ufeff", "")


def _find_column(df: pd.DataFrame, logical_name: str) -> str | None:
    candidates = _COL_EQUIV.get(logical_name, [])
    cols_norm = {_normalize_colname(c): c for c in df.columns}
    for cand in candidates:
        cand_norm = _normalize_colname(cand)
        if cand_norm in cols_norm:
            return cols_norm[cand_norm]
    return None


def _read_csv_safely(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="latin-1")


def _iter_month_clean_csvs(clean_root: Path, month: str) -> Iterable[Path]:
    month_dir = clean_root / month
    if not month_dir.exists():
        return []

    day_dirs = sorted([p for p in month_dir.iterdir() if p.is_dir()])
    files: list[Path] = []
    for day_dir in day_dirs:
        files.extend(sorted(day_dir.glob("*.csv")))
    return files


def build_master_month(
    *,
    month: str,
    clean_root: Path,
    masters_root: Path,
    overwrite: bool = False,
    logger=None,
) -> MasterBuildResult:
    files = list(_iter_month_clean_csvs(clean_root, month))
    if logger:
        logger.info("Master capa_b: month=%s files=%s clean_root=%s", month, len(files), clean_root)

    if not files:
        raise FileNotFoundError(f"No se encontraron CSV CLEAN para el mes {month} en {clean_root}")

    out_dir = masters_root / "capa_b"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"capa_b_actividades_{month}.parquet"

    if out_path.exists() and not overwrite:
        if logger:
            logger.info("Master ya existe (skip): %s", out_path)
        df_exist = pd.read_parquet(out_path)
        return MasterBuildResult(month=month, input_files=0, rows=len(df_exist), output_path=out_path)

    dfs: list[pd.DataFrame] = []
    for file_path in files:
        df = _read_csv_safely(file_path)
        df["__source_file"] = str(file_path)
        dfs.append(df)

    big = pd.concat(dfs, ignore_index=True)

    col_fecha = _find_column(big, "fecha")
    col_id = _find_column(big, "id_actividad")

    if col_fecha:
        parsed = pd.to_datetime(big[col_fecha], errors="coerce", dayfirst=True)
        big["__fecha_sort"] = parsed
    else:
        big["__fecha_sort"] = pd.NaT

    if col_id:
        big["__id_sort"] = big[col_id].astype(str)
    else:
        big["__id_sort"] = ""

    big = big.sort_values(by=["__fecha_sort", "__id_sort"], kind="stable")
    big = big.drop(columns=["__fecha_sort", "__id_sort"])

    big.to_parquet(out_path, index=False)

    if logger:
        logger.info("Master generado: %s rows=%s", out_path, len(big))

    return MasterBuildResult(month=month, input_files=len(files), rows=len(big), output_path=out_path)
