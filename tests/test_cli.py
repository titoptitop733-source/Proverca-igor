"""Tests of the command-line interface.

The real API client is replaced by fakes, so no test touches the network. Every test runs
`cli.main()` against a temporary SQLite database taken from the GT_DB_PATH variable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game_tracker import cli
from game_tracker.api_client import ApiError
from game_tracker.models import Deal, GameDetails, GameSearchResult, Store
from game_tracker.storage import Storage

GAME_ONE = GameDetails(1, "Game One", (Deal(1, 9.99, 19.99, 50.0),), cheapest_ever_price=4.99)


class FakeClient:
    """Stands in for CheapSharkClient: same context-manager interface, no HTTP."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]:
        return [GameSearchResult(1, "Game One", 9.99)]

    def get_game(self, game_id: int) -> GameDetails:
        if game_id != 1:
            raise ApiError(f"Unknown game {game_id}")
        return GAME_ONE

    def get_stores(self) -> list[Store]:
        return [Store(1, "Steam", True)]


class BrokenClient(FakeClient):
    """Every request fails, as when the API is down."""

    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]:
        raise ApiError("API is down")

    def get_game(self, game_id: int) -> GameDetails:
        raise ApiError("API is down")

    def get_stores(self) -> list[Store]:
        raise ApiError("API is down")


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "cli.db"
    monkeypatch.setenv("GT_DB_PATH", str(path))
    monkeypatch.setenv("GT_CHARTS_DIR", str(tmp_path / "charts"))
    monkeypatch.setenv("GT_LOG_LEVEL", "ERROR")
    monkeypatch.setattr(cli, "CheapSharkClient", FakeClient)
    return path


def test_list_on_empty_wishlist(db_path, capsys):
    assert cli.main(["list"]) == 0
    assert "Wishlist is empty" in capsys.readouterr().out


def test_search_prints_results(db_path, capsys):
    assert cli.main(["search", "game"]) == 0
    out = capsys.readouterr().out
    assert "Game One" in out and "$9.99" in out


def test_add_then_list_then_add_again(db_path, capsys):
    assert cli.main(["add", "1", "--target", "10"]) == 0
    assert "Added 'Game One' to wishlist." in capsys.readouterr().out

    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "Game One" in out and "$10.00" in out  # target price shown in the table

    assert cli.main(["add", "1"]) == 0  # adding twice is not an error
    assert "already in your wishlist" in capsys.readouterr().out


def test_add_unknown_game_reports_api_error(db_path, capsys):
    assert cli.main(["add", "999"]) == 1
    assert "API error: Unknown game 999" in capsys.readouterr().err


def test_negative_target_is_rejected_before_any_work(db_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["add", "1", "--target", "-5"])
    assert exc.value.code == 2
    assert "must not be negative" in capsys.readouterr().err


def test_non_numeric_game_id_is_rejected(db_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(["add", "abc"])
    assert exc.value.code == 2


def test_remove_unknown_game_returns_error(db_path, capsys):
    assert cli.main(["remove", "999"]) == 1
    assert "not in your wishlist" in capsys.readouterr().err


def test_target_changes_price_of_tracked_game(db_path, capsys):
    with Storage(db_path) as storage:
        storage.add_game(1, "Game One")

    assert cli.main(["target", "1", "7.5"]) == 0
    assert "$7.50" in capsys.readouterr().out


def test_target_for_unknown_game_returns_error(db_path, capsys):
    assert cli.main(["target", "5", "7.5"]) == 1
    assert "not in your wishlist" in capsys.readouterr().err


def test_api_failure_gives_exit_code_1(db_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "CheapSharkClient", BrokenClient)
    assert cli.main(["search", "game"]) == 1
    assert "API error: API is down" in capsys.readouterr().err


def test_update_reports_failed_game(db_path, monkeypatch, capsys):
    with Storage(db_path) as storage:
        storage.add_game(1, "Game One")
    monkeypatch.setattr(cli, "CheapSharkClient", BrokenClient)

    assert cli.main(["update", "--force"]) == 1  # nothing could be updated
    assert "game 1" in capsys.readouterr().err


def test_invalid_configuration_returns_2(db_path, monkeypatch, capsys):
    monkeypatch.setenv("GT_HTTP_TIMEOUT", "abc")
    assert cli.main(["list"]) == 2
    assert "Configuration error" in capsys.readouterr().err


def test_web_port_out_of_range_is_rejected(db_path, capsys):
    assert cli.main(["web", "--port", "70000", "--no-browser"]) == 2
    assert "Port must be between 1 and 65535" in capsys.readouterr().err
