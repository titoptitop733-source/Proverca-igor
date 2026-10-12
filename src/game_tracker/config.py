"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "https://www.cheapshark.com/api/1.0"
DEFAULT_DB_PATH = "data/game_tracker.db"
DEFAULT_HTTP_TIMEOUT = 10.0
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(Exception):
    """Raised when configuration values are invalid."""


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    db_path: Path
    http_timeout: float
    log_level: str


def load_settings() -> Settings:
    """Load settings from environment (and .env file if present)."""
    load_dotenv()

    timeout_raw = os.getenv("GT_HTTP_TIMEOUT", str(DEFAULT_HTTP_TIMEOUT))
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise ConfigError(f"GT_HTTP_TIMEOUT must be a number, got {timeout_raw!r}") from exc
    if timeout <= 0:
        raise ConfigError("GT_HTTP_TIMEOUT must be greater than 0")

    log_level = os.getenv("GT_LOG_LEVEL", "WARNING").upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ConfigError(f"GT_LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}")

    return Settings(
        api_base_url=os.getenv("GT_API_BASE_URL", DEFAULT_API_BASE_URL),
        db_path=Path(os.getenv("GT_DB_PATH", DEFAULT_DB_PATH)).expanduser(),
        http_timeout=timeout,
        log_level=log_level,
    )
