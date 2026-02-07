from playwright.sync_api import sync_playwright
from pathlib import Path

from core.config.settings import load_settings
from core.config.logging_config import setup_logging
from core.infra.playwright.browser import create_session
from core.infra.playwright.eta_client import EtaClient, EtaCredentials


def main() -> None:
    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    creds = EtaCredentials(username=settings.eta_username, password=settings.eta_password)

    with sync_playwright() as pw:
        session = create_session(
            pw,
            headless=settings.pw_headless,
            slow_mo_ms=settings.pw_slowmo_ms,
            timeout_ms=settings.pw_timeout_ms,
        )
        try:
            client = EtaClient(session.page, settings.eta_base_url)
            logger.info("Abriendo ETA...")
            client.goto_login()
            logger.info("Intentando login (placeholder selectores)...")
            client.login(creds)
            client.assert_logged_in()
            logger.info("Login OK. url=%s", session.page.url)

            shots_dir = settings.paths.log_dir / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            session.page.screenshot(path=str(shots_dir / "login_ok.png"), full_page=True)

        except Exception as e:
            shots_dir = settings.paths.log_dir / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            session.page.screenshot(path=str(shots_dir / "login_error.png"), full_page=True)
            logger.exception("Error en login smoke: %s", e)
            raise
        finally:
            session.close()


if __name__ == "__main__":
    main()