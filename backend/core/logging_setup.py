"""Structured logging for AegisAI — console + optional rotating file."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def configure_logging(
    *,
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: str | None = None,
) -> None:
    """Configure root aegis logger once (safe to call repeatedly)."""
    global _CONFIGURED
    root = logging.getLogger("aegis")
    numeric = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        stream.setLevel(numeric)
        root.addHandler(stream)

    if log_to_file and log_file:
        already = any(
            isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(log_file)
            for h in root.handlers
        )
        if not already:
            from pathlib import Path

            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric)
            root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger; configures handlers from settings on first use."""
    global _CONFIGURED
    if not _CONFIGURED:
        try:
            from config.settings import settings

            configure_logging(
                level=settings.log_level,
                log_to_file=settings.log_to_file,
                log_file=str(settings.log_file) if settings.log_to_file else None,
            )
        except Exception:
            configure_logging(level="INFO", log_to_file=False)
    return logging.getLogger(f"aegis.{name}")
