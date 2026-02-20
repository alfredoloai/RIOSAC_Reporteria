from __future__ import annotations

import argparse
from pathlib import Path

from core.config.logging_config import setup_logging
from core.config.settings import load_settings
from core.layers.capa_b.master import build_master_month


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera master mensual (parquet) desde CLEAN (capa_b).")
    parser.add_argument("--month", help="Mes en formato YYYY-MM. Ej: 2026-01", default=None)
    parser.add_argument("--overwrite", action="store_true", help="Sobrescribe el master si ya existe.")
    return parser.parse_args()


def _discover_months(clean_root: Path) -> list[str]:
    if not clean_root.exists():
        return []
    return sorted(
        [p.name for p in clean_root.iterdir() if p.is_dir() and len(p.name) == 7 and "-" in p.name]
    )


def main() -> None:
    args = _parse_args()
    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    clean_root = settings.paths.data_dir / "clean"
    masters_root = settings.paths.data_dir / "masters"

    if args.month:
        months = [args.month]
    else:
        months = _discover_months(clean_root)

    if not months:
        logger.warning("No hay meses en CLEAN para procesar. clean_root=%s", clean_root)
        return

    for month in months:
        try:
            result = build_master_month(
                month=month,
                clean_root=clean_root,
                masters_root=masters_root,
                overwrite=args.overwrite,
                logger=logger,
            )
            logger.info("OK month=%s rows=%s output=%s", result.month, result.rows, result.output_path)
        except Exception as exc:
            logger.exception("FALLÓ master month=%s: %s", month, exc)


if __name__ == "__main__":
    main()
