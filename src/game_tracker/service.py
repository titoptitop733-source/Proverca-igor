"""Application service used by the GUI.

Every method opens its own short-lived database connection, so methods can safely
run in a background thread (sqlite3 connections must not be shared between threads).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from game_tracker.collector import GameDataSource, UpdateReport, add_to_wishlist, update_wishlist
from game_tracker.config import Settings
from game_tracker.models import GameDetails, GameSearchResult
from game_tracker.overview import GameOverview, build_game_overview, build_wishlist_overview
from game_tracker.storage import Storage


class SearchableSource(GameDataSource, Protocol):
    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]: ...


class TrackerService:
    def __init__(self, source: SearchableSource, settings: Settings) -> None:
        self._source = source
        self._settings = settings

    def _storage(self) -> Storage:
        return Storage(self._settings.db_path)

    def search(self, title: str, limit: int = 20) -> list[GameSearchResult]:
        return self._source.search_games(title, limit=limit)

    def add_game(self, game_id: int, target_price: float | None = None) -> GameDetails | None:
        with self._storage() as storage:
            return add_to_wishlist(self._source, storage, game_id, target_price)

    def remove_game(self, game_id: int) -> bool:
        with self._storage() as storage:
            return storage.remove_game(game_id)

    def set_target_price(self, game_id: int, target_price: float | None) -> bool:
        with self._storage() as storage:
            return storage.set_target_price(game_id, target_price)

    def update_prices(self, force: bool = False) -> UpdateReport:
        interval = timedelta(hours=self._settings.min_snapshot_interval_hours)
        with self._storage() as storage:
            return update_wishlist(self._source, storage, min_interval=interval, force=force)

    def wishlist(self) -> list[GameOverview]:
        with self._storage() as storage:
            return build_wishlist_overview(storage)

    def game_overview(self, game_id: int) -> GameOverview | None:
        with self._storage() as storage:
            return build_game_overview(storage, game_id)
