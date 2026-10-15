"""Application service used by the GUI.

Every method opens its own short-lived database connection, so methods can safely
run in a background thread (sqlite3 connections must not be shared between threads).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from game_tracker.collector import (
    GameDataSource,
    UpdateReport,
    add_to_wishlist,
    sync_stores,
    update_wishlist,
)
from game_tracker.config import Settings
from game_tracker.models import (
    DealListing,
    GameDetails,
    GameSearchResult,
    PricePoint,
    Store,
)
from game_tracker.overview import (
    GameOverview,
    build_game_overview,
    build_wishlist_overview,
)
from game_tracker.storage import Storage


class SearchableSource(GameDataSource, Protocol):
    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]: ...

    def get_deals(
        self,
        *,
        sort_by: str = "Deal Rating",
        store_ids: list[int] | None = None,
        max_price: float | None = None,
        title: str | None = None,
        page: int = 0,
        page_size: int = 30,
    ) -> list[DealListing]: ...


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

    def latest_offers(self, game_id: int) -> list[PricePoint]:
        with self._storage() as storage:
            return storage.latest_snapshot(game_id)

    def tracked_ids(self) -> set[int]:
        with self._storage() as storage:
            return {item.game_id for item in storage.list_games()}

    def stores(self) -> list[Store]:
        """Store list from the database; downloaded once when the database has none."""
        with self._storage() as storage:
            stores = storage.list_stores()
            if not stores:
                sync_stores(self._source, storage)
                stores = storage.list_stores()
            return stores

    def deals(
        self,
        *,
        sort_by: str = "Deal Rating",
        store_ids: list[int] | None = None,
        max_price: float | None = None,
        title: str | None = None,
        page: int = 0,
        page_size: int = 30,
    ) -> list[DealListing]:
        return self._source.get_deals(
            sort_by=sort_by, store_ids=store_ids, max_price=max_price,
            title=title, page=page, page_size=page_size,
        )
