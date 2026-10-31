import pytest

from game_tracker.analysis import Verdict
from game_tracker.config import Settings
from game_tracker.models import Deal, GameDetails, GameSearchResult
from game_tracker.service import TrackerService
from tests.test_collector import FakeSource


class SearchableFake(FakeSource):
    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]:
        return [GameSearchResult(g.game_id, g.title, g.best_deal.price)
                for g in self.games.values() if title.lower() in g.title.lower()][:limit]


@pytest.fixture
def service(tmp_path):
    settings = Settings(
        api_base_url="unused", db_path=tmp_path / "db.sqlite", charts_dir=tmp_path / "charts",
        http_timeout=1, min_snapshot_interval_hours=6, log_level="WARNING",
    )
    games = {
        1: GameDetails(1, "Hollow Knight", (Deal(1, 14.99, 14.99, 0.0),), cheapest_ever_price=2.99),
        2: GameDetails(2, "Celeste", (Deal(1, 4.99, 19.99, 75.0),), cheapest_ever_price=4.99),
    }
    return TrackerService(SearchableFake(games), settings)


def test_search(service):
    assert [r.title for r in service.search("hollow")] == ["Hollow Knight"]


def test_add_and_wishlist_with_advice(service):
    service.add_game(1, target_price=10)
    service.add_game(2)

    advice = {o.item.title: o.advice.verdict for o in service.wishlist()}

    assert advice == {"Celeste": Verdict.BUY_NOW, "Hollow Knight": Verdict.WAIT}


def test_target_remove_and_overview(service):
    service.add_game(1)
    assert service.set_target_price(1, 3.0) is True
    assert service.game_overview(1).item.target_price == 3.0
    assert service.remove_game(1) is True
    assert service.game_overview(1) is None


def test_update_prices_reports_alert(service):
    service.add_game(2, target_price=5.0)
    report = service.update_prices(force=True)
    assert report.updated == [2]
    assert report.alerts[0].title == "Celeste"
