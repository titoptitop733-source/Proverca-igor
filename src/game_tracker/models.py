"""Domain data models used across the application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Store:
    store_id: int
    name: str
    is_active: bool


@dataclass(frozen=True)
class GameSearchResult:
    game_id: int
    title: str
    cheapest_price: float


@dataclass(frozen=True)
class Deal:
    store_id: int
    price: float
    retail_price: float
    savings_percent: float


@dataclass(frozen=True)
class GameDetails:
    game_id: int
    title: str
    deals: tuple[Deal, ...]
    cheapest_ever_price: float | None = None
    cheapest_ever_date: datetime | None = None

    @property
    def best_deal(self) -> Deal | None:
        """Return the cheapest current deal, or None if there are no deals."""
        return min(self.deals, key=lambda deal: deal.price, default=None)


@dataclass(frozen=True)
class WishlistItem:
    game_id: int
    title: str
    target_price: float | None
    added_at: datetime
    cheapest_ever_price: float | None = None


@dataclass(frozen=True)
class PricePoint:
    game_id: int
    store_id: int
    store_name: str | None
    price: float
    retail_price: float
    savings_percent: float
    recorded_at: datetime
