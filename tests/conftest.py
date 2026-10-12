"""Shared fixtures. Sample payloads mimic real CheapShark API responses."""

from pathlib import Path

import pytest

from game_tracker.storage import Storage

SEARCH_RESPONSE = [
    {"gameID": "612", "steamAppID": None, "cheapest": "3.99", "cheapestDealID": "x",
     "external": "LEGO Batman", "internalName": "LEGOBATMAN", "thumb": ""},
    {"gameID": "167613", "steamAppID": "21000", "cheapest": "4.49", "cheapestDealID": "y",
     "external": "LEGO Batman 2", "internalName": "LEGOBATMAN2", "thumb": ""},
]

GAME_RESPONSE = {
    "info": {"title": "LEGO Batman", "steamAppID": None, "thumb": ""},
    "cheapestPriceEver": {"price": "2.99", "date": 1543028665},
    "deals": [
        {"storeID": "1", "dealID": "a", "price": "19.99", "retailPrice": "19.99",
         "savings": "0.000000"},
        {"storeID": "25", "dealID": "b", "price": "3.99", "retailPrice": "19.99",
         "savings": "80.040020"},
    ],
}

STORES_RESPONSE = [
    {"storeID": "1", "storeName": "Steam", "isActive": 1, "images": {}},
    {"storeID": "25", "storeName": "GOG", "isActive": 1, "images": {}},
]


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    db = Storage(tmp_path / "test.db")
    yield db
    db.close()
