from __future__ import annotations

import argparse
from pathlib import Path

from core.config.logging_config import setup_logging
from core.config.settings import load_settings
from core.layers.capa_d.details_extractor import extract_details


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae detalles de órdenes (Capa D) desde ETA.")
    parser.add_argument("--month", required=True, help="Mes en formato YYYY-MM, ej: 2026-02")
    parser.add_argument("--overwrite", action="store_true", help="Ignora manifest y regenera todo")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    try:
        out = extract_details(month=args.month, overwrite=args.overwrite, logger=logger)
        logger.info("Capa D completada: %s", out)
    except Exception as exc:
        logger.exception("Falló capa D: %s", exc)
        raise


if __name__ == "__main__":
    main()
