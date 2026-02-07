from core.config.settings import load_settings
from core.config.logging_config import setup_logging


def main() -> None:
    settings = load_settings()
    logger = setup_logging(settings.paths.log_dir, app_env=settings.app_env)

    logger.info("RIOSAC inicializado")
    logger.info("env=%s data_dir=%s log_dir=%s", settings.app_env, settings.paths.data_dir, settings.paths.log_dir)


if __name__ == "__main__":
    main()