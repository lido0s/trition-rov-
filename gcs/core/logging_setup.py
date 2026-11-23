"""Logging with levels, a rotating file and the console."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    file: str = "logs/gcs.log",
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> None:
    Path(file).parent.mkdir(parents=True, exist_ok=True)
    rotating = logging.handlers.RotatingFileHandler(
        file, maxBytes=max_bytes, backupCount=backup_count
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
        handlers=[rotating, logging.StreamHandler()],
        force=True,
    )
