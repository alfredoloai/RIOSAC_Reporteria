from __future__ import annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import os

from core.config.paths import ProjectPaths, build_paths


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key, str(default)).strip().lower()
    return val in ("1", "true", "yes", "y", "on")


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key, "").strip()
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    # App
    app_env: str

    # ETA
    eta_base_url: str
    eta_username: str
    eta_password: str

    # Playwright
    pw_headless: bool
    pw_slowmo_ms: int
    pw_timeout_ms: int

    # Paths
    paths: ProjectPaths


def load_settings() -> Settings:
    # Carga .env si existe (no falla si no existe)
    load_dotenv(override=False)

    app_env = os.getenv("APP_ENV", "dev")

    eta_base_url = os.getenv("ETA_BASE_URL", "https://claro-ec.etadirect.com/")
    eta_username = os.getenv("ETA_USERNAME", "")
    eta_password = os.getenv("ETA_PASSWORD", "")

    pw_headless = _get_bool("PW_HEADLESS", True)
    pw_slowmo_ms = _get_int("PW_SLOWMO_MS", 0)
    pw_timeout_ms = _get_int("PW_TIMEOUT_MS", 60000)

    project_data_dir = os.getenv("PROJECT_DATA_DIR", "./data")
    project_log_dir = os.getenv("PROJECT_LOG_DIR", "./logs")

    paths = build_paths(project_data_dir=project_data_dir, project_log_dir=project_log_dir)

    return Settings(
        app_env=app_env,
        eta_base_url=eta_base_url,
        eta_username=eta_username,
        eta_password=eta_password,
        pw_headless=pw_headless,
        pw_slowmo_ms=pw_slowmo_ms,
        pw_timeout_ms=pw_timeout_ms,
        paths=paths,
    )