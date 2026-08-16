"""Structured logging setup built on loguru."""

from __future__ import annotations

import sys

from loguru import logger

from app.config import Config

_configured = False


def setup_logging(config: Config) -> None:
    """Configure loguru handlers for the console and the logs directory."""
    global _configured
    if _configured:
        return

    config.logs_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<level>{level}</level> | {time:HH:mm:ss} | {message}",
        colorize=True,
    )
    logger.add(
        config.logs_dir / "scraper_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )
    _configured = True
    logger.debug("Logging configured: level={}", config.log_level)
