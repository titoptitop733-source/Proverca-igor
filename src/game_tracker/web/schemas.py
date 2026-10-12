"""Pydantic models describing the REST API (requests are validated, responses documented)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

MAX_PRICE = 10_000.0


# ---------------------------------------------------------------------- requests

class AddGameIn(BaseModel):
    game_id: int = Field(gt=0, description="CheapShark game ID")
    target_price: float | None = Field(default=None, ge=0, le=MAX_PRICE, description="USD")


class TargetIn(BaseModel):
    target_price: float | None = Field(default=None, ge=0, le=MAX_PRICE, description="USD")


class UpdateIn(BaseModel):
    force: bool = False


# ---------------------------------------------------------------------- responses

class AdviceOut(BaseModel):
    verdict: str          # enum name, e.g. BUY_NOW
    label: str            # human readable, e.g. "BUY NOW"
    reasons: list[str]


class PricePointOut(BaseModel):
    recorded_at: datetime
    price: float
    retail_price: float
    savings_percent: float
    store_id: int
    store_name: str | None


class OfferOut(BaseModel):
    store_id: int
    store_name: str | None
    price: float
    retail_price: float
    savings_percent: float
    is_best: bool


class StatsOut(BaseModel):
    snapshots: int
    first_seen: datetime
    last_seen: datetime
    observed_min: float
    observed_max: float
    average_price: float
    all_time_low: float
    discount_share: float
    max_discount: float
    last_discount_at: datetime | None


class GameSummaryOut(BaseModel):
    game_id: int
    title: str
    cover_url: str | None
    thumb_url: str | None
    current_price: float | None
    retail_price: float | None
    discount_percent: float | None
    store_name: str | None
    all_time_low: float | None
    average_price: float | None
    target_price: float | None
    target_status: str
    price_change: float | None
    at_historical_low: bool
    advice: AdviceOut
    sparkline: list[float]
    last_updated: datetime | None


class GameDetailOut(GameSummaryOut):
    added_at: datetime
    steam_app_id: int | None
    stats: StatsOut | None
    history: list[PricePointOut]
    offers: list[OfferOut]


class ActivityOut(BaseModel):
    kind: str
    game_id: int
    title: str
    message: str
    at: datetime
    change_percent: float | None


class DashboardOut(BaseModel):
    tracked_games: int
    potential_savings: float
    price_drops: int
    historical_lows: int
    targets_reached: int
    featured: GameSummaryOut | None
    activity: list[ActivityOut]


class SearchResultOut(BaseModel):
    game_id: int
    title: str
    cheapest_price: float
    cover_url: str | None
    thumb_url: str | None
    tracked: bool


class DealOut(BaseModel):
    game_id: int
    title: str
    store_id: int
    store_name: str | None
    sale_price: float
    normal_price: float
    savings_percent: float
    metacritic_score: int | None
    steam_rating_text: str | None
    steam_rating_percent: int | None
    cover_url: str | None
    thumb_url: str | None
    last_change: datetime | None
    tracked: bool


class StoreOut(BaseModel):
    store_id: int
    name: str
    is_active: bool


class AlertOut(BaseModel):
    game_id: int
    title: str
    price: float
    target_price: float


class UpdateOut(BaseModel):
    updated: int
    skipped: int
    failed: dict[int, str]
    alerts: list[AlertOut]


class MetaOut(BaseModel):
    version: str
    base_currency: str
    rates: dict[str, float]
    rates_date: str | None
    snapshot_interval_hours: float
    price_source: str
    rates_source: str
