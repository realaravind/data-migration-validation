"""Logging configuration for Ombudsman Validation Studio."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Log directory - configurable via env var
LOG_DIR = Path(os.getenv("OVS_LOG_DIR", "/var/log/ombudsman"))
LOG_FILE = LOG_DIR / "ombudsman.log"
LOG_LEVEL = os.getenv("OVS_LOG_LEVEL", "INFO").upper()
LOG_MAX_SIZE = int(os.getenv("OVS_LOG_MAX_SIZE", 10 * 1024 * 1024))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv("OVS_LOG_BACKUP_COUNT", 5))


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        import json

        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id
        if hasattr(record, "action"):
            log_data["action"] = record.action

        return json.dumps(log_data)


def setup_logging():
    """Configure application logging with file and console handlers."""

    # Create log directory if it doesn't exist
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fall back to local directory if no permission
        global LOG_FILE
        LOG_FILE = Path("./logs/ombudsman.log")
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler - human readable
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler - JSON formatted, rotating
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not create file handler: {e}")

    # Log startup
    logging.info(f"Logging initialized - Level: {LOG_LEVEL}, File: {LOG_FILE}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
