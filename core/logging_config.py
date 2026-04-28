import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(base_dir: Path, debug: bool):
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "kassensturz.log"

    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)


    if logger.handlers:
        return

    # ------------------------
    # Console output
    # ------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ------------------------
    # File output (with rotation)
    # ------------------------
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,   # 2 MB per file
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # always keep full detail in file
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # ------------------------
    # Set log levels
    # ------------------------
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    logger.info("Logging initialized")