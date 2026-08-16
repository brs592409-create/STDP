"""Asynchronous and UI-compatible dual logging system for STDP."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, List


# Custom callback type for UI log listeners
LogListener = Callable[[str, str, str], None]  # (timestamp, level, message)

_listeners: List[LogListener] = []


class UIBridgeLogHandler(logging.Handler):
    """Logging handler that broadcasts formatted records to registered UI listeners."""

    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            timestamp = self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S") if self.formatter else ""
            level = record.levelname
            raw_message = record.getMessage()

            for listener in _listeners:
                try:
                    listener(timestamp, level, raw_message)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def add_log_listener(listener: LogListener) -> None:
    """Register a UI or event callback to receive live log records."""
    if listener not in _listeners:
        _listeners.append(listener)


def remove_log_listener(listener: LogListener) -> None:
    """Unregister a previously added log listener."""
    if listener in _listeners:
        _listeners.remove(listener)


def get_log_dir() -> Path:
    """Return writable directory for log files."""
    if getattr(sys, "frozen", False):
        local_dir = Path(sys.executable).resolve().parent
    else:
        local_dir = Path(__file__).resolve().parent.parent.parent

    # Test if local_dir is writable
    test_file = local_dir / ".stdp_log_test"
    is_writable = False
    try:
        test_file.touch()
        test_file.unlink()
        is_writable = True
    except (PermissionError, OSError):
        is_writable = False

    if is_writable:
        log_dir = local_dir / "logs"
    else:
        local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local_appdata:
            log_dir = Path(local_appdata) / "STDP" / "logs"
        else:
            log_dir = Path.home() / ".stdp" / "logs"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return log_dir


def setup_logger(
    log_dir: Optional[Path] = None,
    level_name: str = "INFO",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Configure root STDP logger with console, rotating file, and UI bridge handlers."""
    if log_dir is None:
        log_dir = get_log_dir()

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    log_file = log_dir / "stdp.log"

    root_logger = logging.getLogger("stdp")
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if not root_logger.handlers:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 1. Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)

        # 2. Rotating File Handler (Safe fallback if file creation fails)
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
        except Exception:
            pass

        # 3. UI Bridge Handler
        ui_handler = UIBridgeLogHandler()
        ui_handler.setFormatter(formatter)
        ui_handler.setLevel(level)
        root_logger.addHandler(ui_handler)

    return root_logger


def get_logger(name: str = "stdp") -> logging.Logger:
    """Retrieve child or named logger for a specific module."""
    if not name.startswith("stdp"):
        name = f"stdp.{name}"
    return logging.getLogger(name)


# Initialize default logger
logger = setup_logger()
