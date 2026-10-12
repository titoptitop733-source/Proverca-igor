"""REST API tests using FastAPI's TestClient (no network, temporary database)."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from game_tracker.api_client import ApiError
from game_tracker.config import Settings
from game_tracker.models import Deal, DealListing, ExchangeRates, GameDetails, GameSearchResult, Store
from game_tracker.service import TrackerService
from game_tracker.web.app import create_app

GAMES = {
    1: GameDetails(1, "Hollow Knight", (Deal(1, 14.99, 14.99, 0.0), Deal(7, 9.99, 14.99, 33.36)),
                   cheapest_ever_price=2.99, steam_app_id=367520,
                   thumb_url="https://example.test/hk.jpg"),
    2: GameDetails(2, "Celeste", (Deal(1, 4.99, 19.99, 75.0),), cheapest_ever_price=4.99),
}


class FakeSource:
    def __init__(self) -> None:
        self.fail = False

    def get_game(self, game_id: int) -> GameDetails:
        if self.fail:
            raise ApiError("CheapShark is down")
        if game_id not in GAMES:
            raise ApiError(f"Game with ID {game_id} was not found")
        return GAMES[game_id]

    def get_stores(self) -> list[Store]:
        return [Store(1, "Steam", True), Store(7, "GOG", True)]

    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]:
        return [GameSearchResult(g.game_id, g.title, g.best_deal.price, g.steam_app_id)
                for g in GAMES.values() if title.lower() in g.title.lower()]

    def get_deals(self, **filters) -> list[DealListing]:
        self.last_filters = filters
        return [DealListing(2, "Celeste", 1, 4.99, 19.99, 75.0, 92, "Very Positive", 95,
                            504230, None, datetime(2026, 10, 1, tzinfo=timezone.utc))]


class FakeRates:
    def get_rates(self):
        return ExchangeRates("USD", {"EUR": 0.86}, "2026-10-09")


@pytest.fixture
def source() -> FakeSource:
    return FakeSource()


@pytest.fixture
def client(tmp_path, source) -> TestClient:
    settings = Settings("unused", tmp_path / "db.sqlite", tmp_path / "charts", 1, 6, "WARNING")
    return TestClient(create_app(TrackerService(source, settings), FakeRates()))


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_meta_contains_rates(client):
    data = client.get("/api/meta").json()
    assert data["rates"] == {"USD": 1.0, "EUR": 0.86}
    assert data["base_currency"] == "USD"


def test_add_list_and_detail(client):
    created = client.post("/api/wishlist", json={"game_id": 1, "target_price": 10})
    assert created.status_code == 201
    body = created.json()
    assert body["current_price"] == 9.99
    assert body["cover_url"].endswith("/367520/header.jpg")
    assert body["target_status"] == "TARGET REACHED"
    assert [o["store_name"] for o in body["offers"]] == ["GOG", "Steam"]
    assert body["offers"][0]["is_best"] is True

    wishlist = client.get("/api/wishlist").json()
    assert [g["title"] for g in wishlist] == ["Hollow Knight"]


def test_duplicate_add_returns_409(client):
    client.post("/api/wishlist", json={"game_id": 2})
    assert client.post("/api/wishlist", json={"game_id": 2}).status_code == 409


@pytest.mark.parametrize("payload", [{"game_id": 0}, {"game_id": 1, "target_price": -5},
                                     {"game_id": "abc"}, {}])
def test_invalid_add_payload_returns_422(client, payload):
    assert client.post("/api/wishlist", json=payload).status_code == 422


def test_unknown_game_returns_502_from_upstream(client):
    response = client.post("/api/wishlist", json={"game_id": 999})
    assert response.status_code == 502
    assert "not found" in response.json()["detail"]


def test_set_target_and_remove(client):
    client.post("/api/wishlist", json={"game_id": 2})
    assert client.put("/api/wishlist/2/target", json={"target_price": 3}).json()["target_price"] == 3
    assert client.delete("/api/wishlist/2").status_code == 204
    assert client.delete("/api/wishlist/2").status_code == 404
    assert client.get("/api/games/2").status_code == 404


def test_dashboard(client):
    client.post("/api/wishlist", json={"game_id": 1})
    client.post("/api/wishlist", json={"game_id": 2})
    data = client.get("/api/dashboard").json()
    assert data["tracked_games"] == 2
    assert data["featured"]["title"] == "Celeste"           # biggest discount
    assert data["potential_savings"] == pytest.approx(5.0 + 15.0)


def test_search_marks_tracked_games(client):
    client.post("/api/wishlist", json={"game_id": 2})
    results = client.get("/api/search", params={"q": "l"}).json()
    tracked = {r["title"]: r["tracked"] for r in results}
    assert tracked == {"Hollow Knight": False, "Celeste": True}


def test_search_requires_query(client):
    assert client.get("/api/search", params={"q": ""}).status_code == 422


def test_deals_pass_filters_and_add_store_names(client, source):
    data = client.get("/api/deals", params={"sort": "Savings", "store": [1, 7],
                                            "max_price": 20}).json()
    assert data[0]["store_name"] == "Steam"
    assert source.last_filters["store_ids"] == [1, 7]
    assert source.last_filters["sort_by"] == "Savings"


def test_deals_reject_unknown_sort(client):
    assert client.get("/api/deals", params={"sort": "Popularity"}).status_code == 422


def test_update_reports_failures_as_data(client, source):
    client.post("/api/wishlist", json={"game_id": 1})
    source.fail = True
    data = client.post("/api/update", json={"force": True}).json()
    assert data["updated"] == 0
    assert "1" in data["failed"]
