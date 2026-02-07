import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: Path, app_env: str = "dev") -> logging.Logger:
    """
    Configura logging para toda la app (core + ui).
    - Consola: INFO
    - Archivo rotativo: DEBUG en dev, INFO en prod
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    logger = logging.getLogger("riosac")
    logger.setLevel(logging.DEBUG)  # manejamos niveles en handlers

    # Evita duplicar handlers si se llama más de una vez
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler consola
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # Handler archivo rotativo
    fh = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=2_000_000,  # ~2MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG if app_env.lower() == "dev" else logging.INFO)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.propagate = False

    logger.debug("Logger inicializado. log_file=%s env=%s", log_file, app_env)
    return logger