from datetime import datetime, timedelta, timezone

from game_tracker.analysis import compute_stats, recommend
from game_tracker.insights import (
    TargetStatus,
    build_dashboard,
    game_events,
    target_status,
)
from game_tracker.models import PricePoint, WishlistItem
from game_tracker.overview import GameOverview

START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def overview(game_id: int, prices: list[float], retail: float = 20.0,
             target: float | None = None, low: float | None = None) -> GameOverview:
    history = [
        PricePoint(game_id, 1, "Steam", p, retail, round((1 - p / retail) * 100, 2),
                   START + timedelta(days=i))
        for i, p in enumerate(prices)
    ]
    item = WishlistItem(game_id, f"Game {game_id}", target, START, low)
    stats = compute_stats(history, low)
    return GameOverview(item, history, stats, recommend(stats, target))


def test_target_status_levels():
    assert target_status(overview(1, [20], target=None)) is TargetStatus.NONE
    assert target_status(overview(1, [10], target=10)) is TargetStatus.REACHED
    assert target_status(overview(1, [11], target=10)) is TargetStatus.ALMOST
    assert target_status(overview(1, [20], target=10)) is TargetStatus.WAITING


def test_events_for_price_drop_low_and_target():
    events = game_events(overview(1, [20, 10], target=12, low=10))
    kinds = [event.kind for event in events]
    assert kinds == ["drop", "low", "target"]
    assert events[0].change_percent == -50.0


def test_no_events_without_change():
    assert game_events(overview(1, [20, 20], low=5)) == []


def test_dashboard_totals_and_featured():
    games = [
        overview(1, [20, 15], low=10),          # 25 % off, dropped
        overview(2, [20, 5], low=5),            # 75 % off, dropped, at low
        overview(3, [20, 20], low=10),          # full price
    ]
    dashboard = build_dashboard(games)

    assert dashboard.tracked_games == 3
    assert dashboard.potential_savings == 20.0      # 5 + 15
    assert dashboard.price_drops == 2
    assert dashboard.historical_lows == 1
    assert dashboard.featured.item.game_id == 2
    assert dashboard.activity[0].at == START + timedelta(days=1)


def test_empty_dashboard():
    dashboard = build_dashboard([])
    assert dashboard.tracked_games == 0
    assert dashboard.featured is None
    assert dashboard.activity == []
