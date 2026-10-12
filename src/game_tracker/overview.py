"""Read-only views combining stored data with analysis (shared by CLI and GUI)."""

from __future__ import annotations

from dataclasses import dataclass

from game_tracker.analysis import PriceStats, Recommendation, compute_stats, recommend
from game_tracker.models import PricePoint, WishlistItem
from game_tracker.storage import Storage


@dataclass(frozen=True)
class GameOverview:
    item: WishlistItem
    history: list[PricePoint]       # best price per snapshot
    stats: PriceStats | None
    advice: Recommendation


def build_game_overview(storage: Storage, game_id: int) -> GameOverview | None:
    item = storage.get_game(game_id)
    if item is None:
        return None
    history = storage.get_best_price_history(game_id)
    stats = compute_stats(history, item.cheapest_ever_price)
    return GameOverview(item, history, stats, recommend(stats, item.target_price))


def build_wishlist_overview(storage: Storage) -> list[GameOverview]:
    overviews = (build_game_overview(storage, item.game_id) for item in storage.list_games())
    return [overview for overview in overviews if overview is not None]
