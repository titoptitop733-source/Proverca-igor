"""Business logic: refreshing prices of the wishlist and detecting price alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from game_tracker.api_client import ApiError
from game_tracker.models import GameDetails, Store
from game_tracker.storage import Storage, utc_now

logger = logging.getLogger(__name__)


class GameDataSource(Protocol):
    """Anything that can provide game data (real API client or a fake in tests)."""

    def get_game(self, game_id: int) -> GameDetails: ...

    def get_stores(self) -> list[Store]: ...


@dataclass(frozen=True)
class PriceAlert:
    game_id: int
    title: str
    store_id: int
    price: float
    target_price: float


@dataclass
class UpdateReport:
    updated: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    failed: dict[int, str] = field(default_factory=dict)
    alerts: list[PriceAlert] = field(default_factory=list)


def sync_stores(source: GameDataSource, storage: Storage) -> bool:
    """Download store names. Failure is not fatal - prices are still usable."""
    try:
        storage.save_stores(source.get_stores())
    except ApiError as exc:
        logger.warning("Could not refresh store list: %s", exc)
        return False
    return True


def save_snapshot(storage: Storage, details: GameDetails, now: datetime | None = None) -> None:
    """Store current deals and the all-time low reported by the API."""
    storage.record_prices(details.game_id, details.deals, recorded_at=now)
    storage.set_cheapest_ever(details.game_id, details.cheapest_ever_price)
    storage.set_game_media(details.game_id, details.steam_app_id, details.thumb_url)


def add_to_wishlist(
    source: GameDataSource, storage: Storage, game_id: int, target_price: float | None = None
) -> GameDetails | None:
    """Validate the game via the API, add it and save the first snapshot.

    Returns the game details, or None if the game was already in the wishlist.
    """
    details = source.get_game(game_id)
    if not storage.add_game(details.game_id, details.title, target_price):
        return None
    sync_stores(source, storage)
    save_snapshot(storage, details)
    return details


def update_wishlist(
    source: GameDataSource,
    storage: Storage,
    now: datetime | None = None,
    min_interval: timedelta = timedelta(hours=6),
    force: bool = False,
) -> UpdateReport:
    """Fetch current prices for every wishlist game and store them as a snapshot.

    Games with a snapshot younger than `min_interval` are skipped (unless `force`),
    so running the command often does not fill the database with duplicates.
    One failing game does not stop the update of the others.
    """
    report = UpdateReport()
    timestamp = now or utc_now()

    for item in storage.list_games():
        last = storage.last_snapshot_at(item.game_id)
        # Games missing data added by newer versions (all-time low, artwork) are never skipped.
        is_recent = last is not None and timestamp - last < min_interval
        is_complete = item.cheapest_ever_price is not None and item.thumb_url is not None
        if not force and is_recent and is_complete:
            report.skipped.append(item.game_id)
            continue

        try:
            details = source.get_game(item.game_id)
        except ApiError as exc:
            logger.error("Failed to update game %s: %s", item.game_id, exc)
            report.failed[item.game_id] = str(exc)
            continue

        save_snapshot(storage, details, now=timestamp)
        report.updated.append(item.game_id)

        best = details.best_deal
        if best is not None and item.target_price is not None and best.price <= item.target_price:
            report.alerts.append(
                PriceAlert(
                    game_id=item.game_id,
                    title=item.title,
                    store_id=best.store_id,
                    price=best.price,
                    target_price=item.target_price,
                )
            )

    logger.info(
        "Updated %d, skipped %d, failed %d",
        len(report.updated), len(report.skipped), len(report.failed),
    )
    return report
