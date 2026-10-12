"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "https://www.cheapshark.com/api/1.0"
DEFAULT_FX_API_URL = "https://api.frankfurter.dev/v1"
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8000
DEFAULT_DB_PATH = "data/game_tracker.db"
DEFAULT_CHARTS_DIR = "data/charts"
DEFAULT_HTTP_TIMEOUT = 10.0
DEFAULT_MIN_SNAPSHOT_INTERVAL_HOURS = 6.0
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(Exception):
    """Raised when configuration values are invalid."""


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    db_path: Path
    charts_dir: Path
    http_timeout: float
    min_snapshot_interval_hours: float
    log_level: str
    fx_api_url: str = DEFAULT_FX_API_URL
    web_host: str = DEFAULT_WEB_HOST
    web_port: int = DEFAULT_WEB_PORT


def _read_float(name: str, default: float, *, allow_zero: bool = False) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc
    if value < 0 or (value == 0 and not allow_zero):
        limit = "0 or more" if allow_zero else "greater than 0"
        raise ConfigError(f"{name} must be {limit}")
    return value


def load_settings() -> Settings:
    """Load settings from environment (and .env file if present)."""
    load_dotenv()

    log_level = os.getenv("GT_LOG_LEVEL", "WARNING").upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ConfigError(f"GT_LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}")

    port_raw = os.getenv("GT_WEB_PORT", str(DEFAULT_WEB_PORT))
    try:
        web_port = int(port_raw)
    except ValueError as exc:
        raise ConfigError(f"GT_WEB_PORT must be an integer, got {port_raw!r}") from exc
    if not 1 <= web_port <= 65535:
        raise ConfigError("GT_WEB_PORT must be between 1 and 65535")

    return Settings(
        api_base_url=os.getenv("GT_API_BASE_URL", DEFAULT_API_BASE_URL),
        db_path=Path(os.getenv("GT_DB_PATH", DEFAULT_DB_PATH)).expanduser(),
        charts_dir=Path(os.getenv("GT_CHARTS_DIR", DEFAULT_CHARTS_DIR)).expanduser(),
        http_timeout=_read_float("GT_HTTP_TIMEOUT", DEFAULT_HTTP_TIMEOUT),
        min_snapshot_interval_hours=_read_float(
            "GT_MIN_SNAPSHOT_INTERVAL_HOURS", DEFAULT_MIN_SNAPSHOT_INTERVAL_HOURS, allow_zero=True
        ),
        log_level=log_level,
        fx_api_url=os.getenv("GT_FX_API_URL", DEFAULT_FX_API_URL),
        web_host=os.getenv("GT_WEB_HOST", DEFAULT_WEB_HOST),
        web_port=web_port,
    )
