import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(base_dir: Path, debug: bool):
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "kassensturz.log"
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    logger = logging.getLogger()
    logger.setLevel(log_level)

    if logger.handlers:
        return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Logging initialized | log_file=%s debug=%s", log_file, debug)
