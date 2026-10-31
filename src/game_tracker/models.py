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
    steam_app_id: int | None = None
    thumb_url: str | None = None


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
    steam_app_id: int | None = None
    thumb_url: str | None = None

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
    steam_app_id: int | None = None
    thumb_url: str | None = None


@dataclass(frozen=True)
class PricePoint:
    game_id: int
    store_id: int
    store_name: str | None
    price: float
    retail_price: float
    savings_percent: float
    recorded_at: datetime


@dataclass(frozen=True)
class DealListing:
    """One discounted offer from the CheapShark deals feed."""

    game_id: int
    title: str
    store_id: int
    sale_price: float
    normal_price: float
    savings_percent: float
    metacritic_score: int | None
    steam_rating_text: str | None
    steam_rating_percent: int | None
    steam_app_id: int | None
    thumb_url: str | None
    last_change: datetime | None


@dataclass(frozen=True)
class ExchangeRates:
    base: str
    rates: dict[str, float]
    date: str
