import logging
import os
import sys
from datetime import datetime
from pathlib import Path


LOG_NAMESPACE = "backend"
LOGS_BASE_DIR = Path(__file__).resolve().parent / "logs"
RUN_TIMESTAMP_ENV_VAR = "EXPENSEAI_RUN_LOG_TIMESTAMP"
RUN_TIMESTAMP = os.environ.get(RUN_TIMESTAMP_ENV_VAR) or datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
os.environ[RUN_TIMESTAMP_ENV_VAR] = RUN_TIMESTAMP
RUN_LOG_DIR = LOGS_BASE_DIR / RUN_TIMESTAMP
RUN_LOG_FILE = RUN_LOG_DIR / "app.log"


def get_run_log_dir() -> Path:
    return RUN_LOG_DIR


def get_run_log_file() -> Path:
    return RUN_LOG_FILE


def _configure_backend_logger() -> None:
    backend_logger = logging.getLogger(LOG_NAMESPACE)
    if getattr(backend_logger, "_expenseai_configured", False):
        return

    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)

    backend_logger.setLevel(logging.DEBUG)
    backend_logger.propagate = False

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(RUN_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    backend_logger.addHandler(console_handler)
    backend_logger.addHandler(file_handler)
    backend_logger._expenseai_configured = True


def setup_logger(name: str = __name__) -> logging.Logger:
    _configure_backend_logger()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger
