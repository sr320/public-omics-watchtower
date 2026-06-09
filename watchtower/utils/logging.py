"""Logging configuration."""

from __future__ import annotations

import logging
from typing import Any


def setup_logging(level: str = "INFO", fmt: str | None = None) -> None:
    """Configure root logger."""
    log_format = fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=log_format)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    parts = [f"{k}={v}" for k, v in kwargs.items()]
    logger.info("%s %s", event, " ".join(parts))
