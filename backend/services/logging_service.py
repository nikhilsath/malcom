"""Application logger configuration and structured log writes.

Primary identifiers: ``configure_application_logger``, ``get_application_logger``,
``write_application_log``, and log file path helpers used during app startup and runtime.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import FastAPI

LOGGER_NAME = "malcom"
DEFAULT_LOG_FILE_NAME = "malcom.log"
DEFAULT_LOG_BACKUP_COUNT = 5


def get_log_dir(root_dir: Path) -> Path:
    return root_dir / "data" / "logs"


def get_log_file_path(root_dir: Path) -> Path:
    return get_log_dir(root_dir) / DEFAULT_LOG_FILE_NAME


def mb_to_bytes(size_mb: int) -> int:
    return size_mb * 1024 * 1024


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [json_safe(item) for item in value]
        return str(value)


def configure_application_logger(app: FastAPI, *, root_dir: Path, max_file_size_mb: int) -> logging.Logger:
    log_dir = get_log_dir(root_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = get_log_file_path(root_dir)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    current_handler: RotatingFileHandler | None = getattr(app.state, "log_handler", None)
    desired_max_bytes = mb_to_bytes(max_file_size_mb)
    should_replace_handler = (
        current_handler is None
        or Path(current_handler.baseFilename) != log_file_path
        or current_handler.maxBytes != desired_max_bytes
    )

    if should_replace_handler:
        if current_handler is not None:
            logger.removeHandler(current_handler)
            current_handler.close()

        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=desired_max_bytes,
            backupCount=DEFAULT_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        app.state.log_handler = handler

    app.state.log_file_path = str(log_file_path)
    app.state.log_file_max_bytes = desired_max_bytes
    return logger


def get_application_logger(app: FastAPI) -> logging.Logger:
    logger = getattr(app.state, "logger", None)
    if isinstance(logger, logging.Logger):
        return logger
    return logging.getLogger(LOGGER_NAME)


def write_application_log(logger: logging.Logger, level: int, event: str, /, **context: Any) -> None:
    payload = {"event": event}
    if context:
        payload["context"] = json_safe(context)
    logger.log(level, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def write_application_exception_log(
    logger: logging.Logger,
    level: int,
    event: str,
    /,
    *,
    error: Exception,
    **context: Any,
) -> None:
    write_application_log(
        logger,
        level,
        event,
        error_type=type(error).__name__,
        error=str(error),
        **context,
    )


__all__ = [
    "DEFAULT_LOG_BACKUP_COUNT",
    "DEFAULT_LOG_FILE_NAME",
    "LOGGER_NAME",
    "configure_application_logger",
    "get_application_logger",
    "get_log_dir",
    "get_log_file_path",
    "json_safe",
    "mb_to_bytes",
    "write_application_exception_log",
    "write_application_log",
]
