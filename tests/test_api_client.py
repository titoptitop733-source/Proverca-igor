import httpx
import pytest

from game_tracker.api_client import ApiError, CheapSharkClient
from tests.conftest import GAME_RESPONSE, SEARCH_RESPONSE, STORES_RESPONSE

BASE_URL = "https://api.example.test/api/1.0"


def make_client(handler) -> CheapSharkClient:
    return CheapSharkClient(BASE_URL, transport=httpx.MockTransport(handler))


def test_search_games_parses_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/1.0/games"
        assert request.url.params["title"] == "batman"
        return httpx.Response(200, json=SEARCH_RESPONSE)

    results = make_client(handler).search_games("  batman ")

    assert len(results) == 2
    assert results[0].game_id == 612
    assert results[0].title == "LEGO Batman"
    assert results[0].cheapest_price == pytest.approx(3.99)


def test_search_rejects_empty_title():
    client = make_client(lambda r: httpx.Response(200, json=[]))
    with pytest.raises(ValueError):
        client.search_games("   ")


def test_get_game_parses_deals_and_best_deal():
    client = make_client(lambda r: httpx.Response(200, json=GAME_RESPONSE))

    game = client.get_game(612)

    assert game.title == "LEGO Batman"
    assert len(game.deals) == 2
    assert game.best_deal is not None
    assert game.best_deal.store_id == 25
    assert game.best_deal.savings_percent == pytest.approx(80.04)
    assert game.cheapest_ever_price == pytest.approx(2.99)
    assert game.cheapest_ever_date is not None


def test_unknown_game_raises_api_error():
    client = make_client(lambda r: httpx.Response(200, json=[]))
    with pytest.raises(ApiError, match="not found"):
        client.get_game(999999)


def test_server_error_is_wrapped():
    client = make_client(lambda r: httpx.Response(500))
    with pytest.raises(ApiError, match="HTTP 500"):
        client.get_game(612)


def test_rate_limit_has_clear_message():
    client = make_client(lambda r: httpx.Response(429))
    with pytest.raises(ApiError, match="rate limit"):
        client.get_stores()


def test_timeout_is_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ApiError, match="in time"):
        make_client(handler).get_stores()


def test_invalid_price_in_response_raises_api_error():
    bad = [{**SEARCH_RESPONSE[0], "cheapest": "free!"}]
    client = make_client(lambda r: httpx.Response(200, json=bad))
    with pytest.raises(ApiError, match="cheapest"):
        client.search_games("batman")


def test_get_stores():
    stores = make_client(lambda r: httpx.Response(200, json=STORES_RESPONSE)).get_stores()
    assert [s.name for s in stores] == ["Steam", "GOG"]


DEALS_RESPONSE = [
    {"internalName": "CELESTE", "title": "Celeste", "dealID": "x", "storeID": "1",
     "gameID": "100", "salePrice": "4.99", "normalPrice": "19.99", "isOnSale": "1",
     "savings": "75.037519", "metacriticScore": "92", "steamRatingText": "Overwhelmingly Positive",
     "steamRatingPercent": "97", "steamAppID": "504230", "releaseDate": 1516665600,
     "lastChange": 1760000000, "dealRating": "9.5",
     "thumb": "https://shared.steamstatic.com/thumb.jpg"},
    {"internalName": "X", "title": "No Steam", "dealID": "y", "storeID": "7", "gameID": "101",
     "salePrice": "1.00", "normalPrice": "2.00", "savings": "50", "metacriticScore": "0",
     "steamRatingText": None, "steamRatingPercent": "0", "steamAppID": None,
     "lastChange": 0, "thumb": "javascript:alert(1)"},
]


def test_get_deals_parses_and_sends_filters():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/1.0/deals"
        assert request.url.params["onSale"] == "1"
        assert request.url.params["storeID"] == "1,7"
        assert request.url.params["upperPrice"] == "15.0"
        return httpx.Response(200, json=DEALS_RESPONSE)

    deals = make_client(handler).get_deals(store_ids=[1, 7], max_price=15.0)

    assert deals[0].title == "Celeste"
    assert deals[0].steam_app_id == 504230
    assert deals[0].metacritic_score == 92
    assert deals[0].last_change is not None
    assert deals[1].metacritic_score is None        # "0" means unknown
    assert deals[1].thumb_url is None               # unsafe URL rejected


def test_get_deals_validates_arguments():
    client = make_client(lambda r: httpx.Response(200, json=[]))
    with pytest.raises(ValueError):
        client.get_deals(sort_by="Popularity")
    with pytest.raises(ValueError):
        client.get_deals(page_size=100)
