"""Business logic: refreshing prices of the wishlist and detecting price alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
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


def update_wishlist(
    source: GameDataSource, storage: Storage, now: datetime | None = None
) -> UpdateReport:
    """Fetch current prices for every wishlist game and store them as a snapshot.

    One failing game does not stop the update of the others.
    """
    report = UpdateReport()
    timestamp = now or utc_now()

    for item in storage.list_games():
        try:
            details = source.get_game(item.game_id)
        except ApiError as exc:
            logger.error("Failed to update game %s: %s", item.game_id, exc)
            report.failed[item.game_id] = str(exc)
            continue

        storage.record_prices(item.game_id, details.deals, recorded_at=timestamp)
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

    logger.info("Updated %d games, %d failed", len(report.updated), len(report.failed))
    return report
