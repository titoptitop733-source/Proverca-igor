from game_tracker.api_client import ApiError
from game_tracker.collector import sync_stores, update_wishlist
from game_tracker.models import Deal, GameDetails, Store


class FakeSource:
    """Test double for CheapSharkClient - no network involved."""

    def __init__(self, games: dict[int, GameDetails], failing: set[int] | None = None):
        self.games = games
        self.failing = failing or set()

    def get_game(self, game_id: int) -> GameDetails:
        if game_id in self.failing:
            raise ApiError("boom")
        return self.games[game_id]

    def get_stores(self) -> list[Store]:
        raise ApiError("stores unavailable")


def make_game(game_id: int, price: float) -> GameDetails:
    return GameDetails(game_id, f"Game {game_id}", (Deal(1, price, 20.0, 50.0),))


def test_update_records_prices_and_creates_alert(storage):
    storage.add_game(1, "Game 1", target_price=10.0)
    storage.add_game(2, "Game 2", target_price=5.0)
    source = FakeSource({1: make_game(1, 9.99), 2: make_game(2, 7.0)})

    report = update_wishlist(source, storage)

    assert sorted(report.updated) == [1, 2]
    assert [a.game_id for a in report.alerts] == [1]  # only game 1 is below target
    assert len(storage.get_history(1)) == 1


def test_one_failing_game_does_not_stop_others(storage):
    storage.add_game(1, "Game 1")
    storage.add_game(2, "Game 2")
    source = FakeSource({2: make_game(2, 7.0)}, failing={1})

    report = update_wishlist(source, storage)

    assert report.updated == [2]
    assert 1 in report.failed


def test_sync_stores_failure_is_not_fatal(storage):
    assert sync_stores(FakeSource({}), storage) is False


def test_recent_snapshot_is_skipped_unless_forced(storage):
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 5, 1, 12, tzinfo=timezone.utc)
    storage.add_game(1, "Game 1")
    storage.set_cheapest_ever(1, 4.0)
    storage.set_game_media(1, 123, "https://example.test/thumb.jpg")
    storage.record_prices(1, [Deal(1, 9.0, 20.0, 55.0)], recorded_at=now - timedelta(hours=1))
    source = FakeSource({1: make_game(1, 9.99)})

    skipped = update_wishlist(source, storage, now=now, min_interval=timedelta(hours=6))
    forced = update_wishlist(source, storage, now=now, force=True)

    assert skipped.skipped == [1] and skipped.updated == []
    assert forced.updated == [1]


def test_update_saves_cheapest_ever(storage):
    storage.add_game(1, "Game 1")
    game = GameDetails(1, "Game 1", (Deal(1, 10.0, 20.0, 50.0),), cheapest_ever_price=3.5)

    update_wishlist(FakeSource({1: game}), storage)

    assert storage.get_game(1).cheapest_ever_price == 3.5


def test_game_without_all_time_low_is_not_skipped(storage):
    """Regression: games added by v0.1 had no all-time low and were skipped forever."""
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 5, 1, 12, tzinfo=timezone.utc)
    storage.add_game(1, "Game 1")
    storage.record_prices(1, [Deal(1, 9.0, 20.0, 55.0)], recorded_at=now - timedelta(hours=1))
    game = GameDetails(1, "Game 1", (Deal(1, 9.0, 20.0, 55.0),), cheapest_ever_price=2.99)

    report = update_wishlist(FakeSource({1: game}), storage, now=now)

    assert report.updated == [1]
    assert storage.get_game(1).cheapest_ever_price == 2.99


def test_add_to_wishlist_saves_first_snapshot(storage):
    from game_tracker.collector import add_to_wishlist

    game = GameDetails(7, "Game 7", (Deal(1, 5.0, 10.0, 50.0),), cheapest_ever_price=3.0)
    source = FakeSource({7: game})

    assert add_to_wishlist(source, storage, 7, target_price=4.0) == game
    assert add_to_wishlist(source, storage, 7) is None  # already there
    assert len(storage.get_history(7)) == 1
    assert storage.get_game(7).cheapest_ever_price == 3.0
