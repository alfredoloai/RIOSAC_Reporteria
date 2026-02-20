from __future__ import annotations

import argparse
from pathlib import Path

from core.config.logging_config import setup_logging
from core.config.settings import load_settings
from core.layers.capa_c.ids_queue import generate_ids_queue


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera queue de IDs únicos desde masters capa_b.")
    parser.add_argument("--month", help="Mes en formato YYYY-MM. Ej: 2026-01", default=None)
    parser.add_argument("--overwrite", action="store_true", help="Sobrescribe el archivo queue si ya existe.")
    return parser.parse_args()


def _discover_months(masters_root: Path) -> list[str]:
    capa_b_dir = masters_root / "capa_b"
    if not capa_b_dir.exists():
        return []
    months: list[str] = []
    for file_path in capa_b_dir.glob("capa_b_actividades_*.parquet"):
        name = file_path.stem.replace("capa_b_actividades_", "")
        if len(name) == 7 and "-" in name:
            months.append(name)
    return sorted(months)


def main() -> None:
    args = _parse_args()
    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    masters_root = settings.paths.data_dir / "masters"

    if args.month:
        months = [args.month]
    else:
        months = _discover_months(masters_root)

    if not months:
        logger.warning("No se encontraron masters capa_b para generar colas. masters_root=%s", masters_root)
        return

    for month in months:
        try:
            generate_ids_queue(
                month=month,
                masters_root=masters_root,
                overwrite=args.overwrite,
                logger=logger,
            )
        except Exception as exc:
            logger.exception("FALLÓ queue month=%s: %s", month, exc)


if __name__ == "__main__":
    main()
