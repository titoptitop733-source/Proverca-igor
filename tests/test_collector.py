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
