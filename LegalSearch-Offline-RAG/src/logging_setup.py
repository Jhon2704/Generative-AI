from __future__ import annotations

import logging
import sys
from pathlib import Path

from utils import get_app_data_dir


_LOGGER_INITIALIZED = False


def setup_logging() -> Path:
    global _LOGGER_INITIALIZED
    app_dir = get_app_data_dir("LegalSearchOffline")
    log_dir = app_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    if not _LOGGER_INITIALIZED:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        has_file = any(
            isinstance(handler, logging.FileHandler)
            and Path(getattr(handler, "baseFilename", "")).resolve() == log_file.resolve()
            for handler in root_logger.handlers
        )
        if not has_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        has_console = any(
            isinstance(handler, logging.StreamHandler)
            and getattr(handler, "stream", None) is sys.stdout
            for handler in root_logger.handlers
        )
        if not has_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        _LOGGER_INITIALIZED = True

    return log_file


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
