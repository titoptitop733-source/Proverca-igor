import pytest

from game_tracker.config import ConfigError, load_settings


def test_defaults(monkeypatch):
    for name in ("GT_HTTP_TIMEOUT", "GT_MIN_SNAPSHOT_INTERVAL_HOURS", "GT_LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("game_tracker.config.load_dotenv", lambda: None)

    settings = load_settings()

    assert settings.http_timeout == 10.0
    assert settings.min_snapshot_interval_hours == 6.0


@pytest.mark.parametrize(
    ("name", "value"),
    [("GT_HTTP_TIMEOUT", "abc"), ("GT_HTTP_TIMEOUT", "0"),
     ("GT_MIN_SNAPSHOT_INTERVAL_HOURS", "-1"), ("GT_LOG_LEVEL", "LOUD")],
)
def test_invalid_values_raise(monkeypatch, name, value):
    monkeypatch.setattr("game_tracker.config.load_dotenv", lambda: None)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError):
        load_settings()


def test_zero_interval_is_allowed(monkeypatch):
    monkeypatch.setattr("game_tracker.config.load_dotenv", lambda: None)
    monkeypatch.setenv("GT_MIN_SNAPSHOT_INTERVAL_HOURS", "0")
    assert load_settings().min_snapshot_interval_hours == 0
