from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

from core.config.settings import load_settings
from core.config.logging_config import setup_logging
from core.infra.playwright.browser import create_session
from core.infra.playwright.eta_client import EtaClient, EtaCredentials
from core.storage.filesystem import build_raw_target
from core.utils.dates import iter_dates


@dataclass(frozen=True)
class ExportResult:
	group_name: str
	saved_to: Path


def export_capa_a_raw(
	groups: Iterable[str],
	start_date: date | None = None,
	end_date: date | None = None,
) -> list[ExportResult]:
	settings = load_settings()
	logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

	start = start_date or date.today()
	end = end_date or start
	if end < start:
		raise ValueError("end_date no puede ser anterior a start_date")

	creds = EtaCredentials(username=settings.eta_username, password=settings.eta_password)

	results: list[ExportResult] = []

	with sync_playwright() as pw:
		session = create_session(
			pw,
			headless=settings.pw_headless,
			slow_mo_ms=settings.pw_slowmo_ms,
			timeout_ms=settings.pw_timeout_ms,
		)
		client = EtaClient(session.page, settings.eta_base_url)

		try:
			logger.info("Login ETA...")
			client.login(creds)
			client.assert_logged_in()
			logger.info("Login OK")

			for current_day in iter_dates(start, end):
				logger.info("Configurando fecha de despacho: %s", current_day.isoformat())
				client.set_dispatch_date(current_day)
				client.page.wait_for_timeout(500)
				client.page.wait_for_load_state("networkidle")

				for g in groups:
					try:
						logger.info("Seleccionando cuadrilla: %s", g)
						client.select_group(g)

						logger.info("Exportando CSV: %s", g)
						download = client.export_csv_from_actions()

						target = build_raw_target(settings.paths.raw_dir, current_day, g)
						download.save_as(str(target.file_path))

						logger.info("CSV guardado: %s", target.file_path)
						results.append(ExportResult(group_name=g, saved_to=target.file_path))
					except Exception:
						logger.exception(
							"Falló export en grupo=%s día=%s. Se continúa.",
							g,
							current_day.isoformat(),
						)
						continue

			return results

		finally:
			# Para evitar sesiones abiertas
			try:
				logger.info("Logout...")
				client.logout()
				logger.info("Logout OK")
			except Exception as e:
				logger.warning("No se pudo hacer logout: %s", e)

			session.close()
