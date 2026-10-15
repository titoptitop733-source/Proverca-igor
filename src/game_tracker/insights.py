"""Dashboard insights derived from wishlist overviews: target status, activity, totals."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from game_tracker.overview import GameOverview

ALMOST_THERE_RATIO = 0.15      # current price at most 15 % above the target
PRICE_TOLERANCE = 0.01         # prices are compared with one-cent tolerance


class TargetStatus(str, Enum):
    REACHED = "TARGET REACHED"
    ALMOST = "ALMOST THERE"
    WAITING = "WAITING FOR DROP"
    NONE = "NO TARGET"


@dataclass(frozen=True)
class ActivityEvent:
    kind: str                      # "drop", "rise", "low" or "target"
    game_id: int
    title: str
    message: str
    at: datetime
    change_percent: float | None = None


@dataclass(frozen=True)
class DashboardSummary:
    tracked_games: int
    potential_savings: float
    price_drops: int
    historical_lows: int
    targets_reached: int
    featured: GameOverview | None
    activity: list[ActivityEvent]


def target_status(overview: GameOverview) -> TargetStatus:
    target, stats = overview.item.target_price, overview.stats
    if target is None or stats is None:
        return TargetStatus.NONE
    if stats.current_price <= target + PRICE_TOLERANCE:
        return TargetStatus.REACHED
    if stats.current_price <= target * (1 + ALMOST_THERE_RATIO):
        return TargetStatus.ALMOST
    return TargetStatus.WAITING


def price_change(overview: GameOverview) -> float | None:
    """Difference between the last two snapshots (negative = cheaper)."""
    if len(overview.history) < 2:
        return None
    return round(overview.history[-1].price - overview.history[-2].price, 2)


def is_at_historical_low(overview: GameOverview) -> bool:
    stats = overview.stats
    return stats is not None and stats.current_price <= stats.all_time_low + PRICE_TOLERANCE


def game_events(overview: GameOverview) -> list[ActivityEvent]:
    stats = overview.stats
    if stats is None:
        return []
    game_id, title, at = overview.item.game_id, overview.item.title, stats.last_seen
    events: list[ActivityEvent] = []

    change = price_change(overview)
    if change:
        previous = overview.history[-2].price
        percent = change / previous * 100 if previous else 0.0
        kind, verb = ("drop", "dropped") if change < 0 else ("rise", "increased")
        events.append(ActivityEvent(
            kind, game_id, title,
            f"Price {verb} by {abs(percent):.0f}% (${previous:.2f} → ${stats.current_price:.2f})",
            at, round(percent, 1),
        ))
    if is_at_historical_low(overview) and stats.current_discount > 0:
        events.append(ActivityEvent("low", game_id, title, "At its historical low price", at))
    if target_status(overview) is TargetStatus.REACHED:
        events.append(ActivityEvent("target", game_id, title, "Your target price was reached", at))
    return events


def build_dashboard(
    overviews: Sequence[GameOverview], activity_limit: int = 12
) -> DashboardSummary:
    # Only games with at least one recorded price take part in the price calculations.
    priced = [(o, o.stats) for o in overviews if o.stats is not None]
    discounted = [(o, stats) for o, stats in priced if stats.current_discount > 0]
    featured = max(
        discounted,
        key=lambda pair: (pair[1].current_discount, pair[1].retail_price - pair[1].current_price),
        default=None,
    )
    events = [event for o in overviews for event in game_events(o)]
    events.sort(key=lambda event: event.at, reverse=True)

    return DashboardSummary(
        tracked_games=len(overviews),
        potential_savings=round(
            sum(max(stats.retail_price - stats.current_price, 0.0) for _, stats in priced), 2
        ),
        price_drops=sum(1 for o in overviews if (price_change(o) or 0) < 0),
        historical_lows=sum(1 for o, _ in priced if is_at_historical_low(o)),
        targets_reached=sum(1 for o in overviews if target_status(o) is TargetStatus.REACHED),
        featured=featured[0] if featured else None,
        activity=events[:activity_limit],
    )
