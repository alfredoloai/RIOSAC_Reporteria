from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

from core.config.logging_config import setup_logging
from core.config.settings import load_settings
from core.infra.playwright.browser import create_session
from core.infra.playwright.eta_client import EtaClient, EtaCredentials
from core.layers.capa_b import run_build_master, run_clean
from core.layers.capa_c import run_generate_queue
from core.layers.capa_d import run_extract_details
from core.storage.filesystem import build_raw_target
from core.utils.dates import iter_dates


GROUPS = [
    "Retiro de equipos Gpon Riosactelcom",
    "Cañar / Riosactelcom",
    "Cuenca / Riosactelcom",
    "GYE,Centro Riosactelcom",
    "Machala / Riosactelcom",
    "Riosactelcom / Loja",
]


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _reset_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True, exist_ok=True)


def run_full_pipeline(start: date, end: date, *, month: str, logger) -> None:
    settings = load_settings()

    logger.info("Reiniciando data en %s", settings.paths.data_dir)
    _reset_dirs(
        [
            settings.paths.raw_dir,
            settings.paths.clean_dir,
            settings.paths.masters_dir,
            settings.paths.manifests_dir,
        ]
    )

    with sync_playwright() as pw:
        session = create_session(
            pw,
            headless=settings.pw_headless,
            slow_mo_ms=settings.pw_slowmo_ms,
            timeout_ms=settings.pw_timeout_ms,
        )
        client = EtaClient(session.page, settings.eta_base_url)
        creds = EtaCredentials(
            username=settings.eta_username,
            password=settings.eta_password,
        )

        logger.info("Login ETA...")
        client.login(creds)
        client.assert_logged_in()
        logger.info("Login OK")

        # CAPA A: Exportar raw usando la sesión viva
        logger.info("[A] Export RAW %s -> %s", start, end)
        for current_day in iter_dates(start, end):
            logger.info("Configurando fecha de despacho: %s", current_day.isoformat())
            client.set_dispatch_date(current_day)
            client.page.wait_for_timeout(400)
            for g in GROUPS:
                try:
                    logger.info("Exportando CSV: %s", g)
                    client.select_group(g)
                    download = client.export_csv_from_actions()
                    target = build_raw_target(settings.paths.raw_dir, current_day, g)
                    download.save_as(str(target.file_path))
                    logger.info("CSV guardado: %s", target.file_path)
                except Exception:
                    logger.exception("Falló export en grupo=%s día=%s. Continúa.", g, current_day.isoformat())
                    continue

        # CAPA B: Clean + master (offline)
        logger.info("[B] Clean")
        sys.argv = ["run_clean"]
        run_clean.main()

        logger.info("[B] Build master")
        sys.argv = ["run_build_master", "--month", month, "--overwrite"]
        run_build_master.main()

        # CAPA C: Queue
        logger.info("[C] Queue IDs")
        sys.argv = ["run_generate_queue", "--month", month, "--overwrite"]
        run_generate_queue.main()

        # CAPA D: Detalles reutilizando la misma sesión (sigue logueada)
        logger.info("[D] Extract details")
        run_extract_details.extract_details(
            month=month,
            overwrite=True,
            logger=logger,
            session=session,
            eta_client=client,
        )

        try:
            client.logout()
        except Exception:
            logger.warning("No se pudo hacer logout (se cierra el navegador igualmente)")
        session.close()

    logger.info("Pipeline completo: mes=%s", month)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta pipeline completo A->D")
    parser.add_argument("--start", required=False, type=_parse_date, help="YYYY-MM-DD (default hoy)")
    parser.add_argument("--end", required=False, type=_parse_date, help="YYYY-MM-DD (default start)")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    start = args.start or date.today()
    end = args.end or start
    if end < start:
        raise SystemExit("end no puede ser menor que start")
    month = end.strftime("%Y-%m")

    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    run_full_pipeline(start, end, month=month, logger=logger)


if __name__ == "__main__":
    main()
