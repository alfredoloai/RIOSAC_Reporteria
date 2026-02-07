from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    log_dir: Path

    # data subfolders
    raw_dir: Path
    clean_dir: Path
    daily_dir: Path
    masters_dir: Path

    daily_capa_a: Path
    daily_capa_b: Path
    daily_capa_c: Path

    masters_capa_a: Path
    masters_capa_b: Path
    masters_capa_c: Path


def build_paths(project_data_dir: str, project_log_dir: str) -> ProjectPaths:
    root = Path.cwd()

    data_dir = (root / project_data_dir).resolve()
    log_dir = (root / project_log_dir).resolve()

    raw_dir = data_dir / "raw"
    clean_dir = data_dir / "clean"
    daily_dir = data_dir / "daily"
    masters_dir = data_dir / "masters"

    daily_capa_a = daily_dir / "capa_a"
    daily_capa_b = daily_dir / "capa_b"
    daily_capa_c = daily_dir / "capa_c"

    masters_capa_a = masters_dir / "capa_a"
    masters_capa_b = masters_dir / "capa_b"
    masters_capa_c = masters_dir / "capa_c"

    # Crear todo (idempotente)
    for p in [
        data_dir,
        log_dir,
        raw_dir,
        clean_dir,
        daily_dir,
        masters_dir,
        daily_capa_a,
        daily_capa_b,
        daily_capa_c,
        masters_capa_a,
        masters_capa_b,
        masters_capa_c,
    ]:
        p.mkdir(parents=True, exist_ok=True)

    return ProjectPaths(
        root=root,
        data_dir=data_dir,
        log_dir=log_dir,
        raw_dir=raw_dir,
        clean_dir=clean_dir,
        daily_dir=daily_dir,
        masters_dir=masters_dir,
        daily_capa_a=daily_capa_a,
        daily_capa_b=daily_capa_b,
        daily_capa_c=daily_capa_c,
        masters_capa_a=masters_capa_a,
        masters_capa_b=masters_capa_b,
        masters_capa_c=masters_capa_c,
    )