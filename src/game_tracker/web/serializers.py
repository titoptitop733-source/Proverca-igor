"""Conversion of domain objects to API response models."""

from __future__ import annotations

from collections.abc import Iterable

from game_tracker.collector import UpdateReport
from game_tracker.insights import (
    ActivityEvent,
    DashboardSummary,
    is_at_historical_low,
    price_change,
    target_status,
)
from game_tracker.models import DealListing, GameSearchResult, PricePoint, Store
from game_tracker.overview import GameOverview
from game_tracker.web.schemas import (
    ActivityOut,
    AdviceOut,
    AlertOut,
    DashboardOut,
    DealOut,
    GameDetailOut,
    GameSummaryOut,
    OfferOut,
    PricePointOut,
    SearchResultOut,
    StatsOut,
    StoreOut,
    UpdateOut,
)

SPARKLINE_POINTS = 30
STEAM_HEADER_URL = "https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"


def cover_url(steam_app_id: int | None, thumb_url: str | None) -> str | None:
    """Wide Steam header artwork when the game is on Steam, otherwise CheapShark thumbnail."""
    if steam_app_id:
        return STEAM_HEADER_URL.format(app_id=int(steam_app_id))
    return thumb_url


def summary(overview: GameOverview) -> GameSummaryOut:
    item, stats = overview.item, overview.stats
    return GameSummaryOut(
        game_id=item.game_id,
        title=item.title,
        cover_url=cover_url(item.steam_app_id, item.thumb_url),
        thumb_url=item.thumb_url,
        current_price=stats.current_price if stats else None,
        retail_price=stats.retail_price if stats else None,
        discount_percent=stats.current_discount if stats else None,
        store_name=stats.current_store if stats else None,
        all_time_low=stats.all_time_low if stats else item.cheapest_ever_price,
        average_price=stats.average_price if stats else None,
        target_price=item.target_price,
        target_status=target_status(overview).value,
        price_change=price_change(overview),
        at_historical_low=is_at_historical_low(overview),
        advice=AdviceOut(
            verdict=overview.advice.verdict.name,
            label=overview.advice.verdict.value,
            reasons=list(overview.advice.reasons),
        ),
        sparkline=[point.price for point in overview.history[-SPARKLINE_POINTS:]],
        last_updated=stats.last_seen if stats else None,
    )


def _point(point: PricePoint) -> PricePointOut:
    return PricePointOut(
        recorded_at=point.recorded_at, price=point.price, retail_price=point.retail_price,
        savings_percent=point.savings_percent, store_id=point.store_id,
        store_name=point.store_name,
    )


def detail(overview: GameOverview, offers: list[PricePoint]) -> GameDetailOut:
    stats = overview.stats
    best_price = min((offer.price for offer in offers), default=None)
    return GameDetailOut(
        **summary(overview).model_dump(),
        added_at=overview.item.added_at,
        steam_app_id=overview.item.steam_app_id,
        stats=StatsOut(
            snapshots=stats.snapshots, first_seen=stats.first_seen, last_seen=stats.last_seen,
            observed_min=stats.observed_min, observed_max=stats.observed_max,
            average_price=stats.average_price, all_time_low=stats.all_time_low,
            discount_share=stats.discount_share, max_discount=stats.max_discount,
            last_discount_at=stats.last_discount_at,
        ) if stats else None,
        history=[_point(point) for point in overview.history],
        offers=[
            OfferOut(
                store_id=offer.store_id, store_name=offer.store_name, price=offer.price,
                retail_price=offer.retail_price, savings_percent=offer.savings_percent,
                is_best=offer.price == best_price,
            )
            for offer in offers
        ],
    )


def activity(event: ActivityEvent) -> ActivityOut:
    return ActivityOut(
        kind=event.kind, game_id=event.game_id, title=event.title, message=event.message,
        at=event.at, change_percent=event.change_percent,
    )


def dashboard(summary_data: DashboardSummary) -> DashboardOut:
    return DashboardOut(
        tracked_games=summary_data.tracked_games,
        potential_savings=summary_data.potential_savings,
        price_drops=summary_data.price_drops,
        historical_lows=summary_data.historical_lows,
        targets_reached=summary_data.targets_reached,
        featured=summary(summary_data.featured) if summary_data.featured else None,
        activity=[activity(event) for event in summary_data.activity],
    )


def search_result(result: GameSearchResult, tracked: set[int]) -> SearchResultOut:
    return SearchResultOut(
        game_id=result.game_id, title=result.title, cheapest_price=result.cheapest_price,
        cover_url=cover_url(result.steam_app_id, result.thumb_url),
        thumb_url=result.thumb_url, tracked=result.game_id in tracked,
    )


def deal(listing: DealListing, store_names: dict[int, str], tracked: set[int]) -> DealOut:
    return DealOut(
        game_id=listing.game_id, title=listing.title, store_id=listing.store_id,
        store_name=store_names.get(listing.store_id), sale_price=listing.sale_price,
        normal_price=listing.normal_price, savings_percent=listing.savings_percent,
        metacritic_score=listing.metacritic_score,
        steam_rating_text=listing.steam_rating_text,
        steam_rating_percent=listing.steam_rating_percent,
        cover_url=cover_url(listing.steam_app_id, listing.thumb_url),
        thumb_url=listing.thumb_url, last_change=listing.last_change,
        tracked=listing.game_id in tracked,
    )


def stores(items: Iterable[Store]) -> list[StoreOut]:
    return [StoreOut(store_id=s.store_id, name=s.name, is_active=s.is_active) for s in items]


def update_report(report: UpdateReport) -> UpdateOut:
    return UpdateOut(
        updated=len(report.updated), skipped=len(report.skipped), failed=report.failed,
        alerts=[
            AlertOut(game_id=a.game_id, title=a.title, price=a.price, target_price=a.target_price)
            for a in report.alerts
        ],
    )
