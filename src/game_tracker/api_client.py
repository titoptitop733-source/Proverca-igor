"""HTTP client for the public CheapShark API (https://apidocs.cheapshark.com/)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from game_tracker.models import Deal, GameDetails, GameSearchResult, Store

logger = logging.getLogger(__name__)

USER_AGENT = "game-price-tracker/0.1 (student project)"


class ApiError(Exception):
    """Raised when the API cannot be reached or returns unexpected data."""


class CheapSharkClient:
    """Thin wrapper over CheapShark endpoints that returns domain models."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # `transport` allows tests to inject httpx.MockTransport (no network needed).
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CheapSharkClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------ public API

    def search_games(self, title: str, limit: int = 10) -> list[GameSearchResult]:
        """Search games by title."""
        title = title.strip()
        if not title:
            raise ValueError("Search title must not be empty")
        if not 1 <= limit <= 60:
            raise ValueError("Limit must be between 1 and 60")

        data = self._get("games", {"title": title, "limit": limit})
        if not isinstance(data, list):
            raise ApiError("Unexpected response format for game search")
        return [_parse_search_result(item) for item in data]

    def get_game(self, game_id: int) -> GameDetails:
        """Return details and all current deals for a single game."""
        if game_id <= 0:
            raise ValueError("Game ID must be a positive number")

        data = self._get("games", {"id": game_id})
        # For an unknown ID the API returns an empty list instead of an object.
        if not isinstance(data, dict) or "info" not in data:
            raise ApiError(f"Game with ID {game_id} was not found")
        return _parse_game_details(game_id, data)

    def get_stores(self) -> list[Store]:
        """Return all stores known to CheapShark."""
        data = self._get("stores")
        if not isinstance(data, list):
            raise ApiError("Unexpected response format for stores")
        return [_parse_store(item) for item in data]

    # ------------------------------------------------------------------ internals

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        logger.debug("GET %s params=%s", path, params)
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ApiError("CheapShark API did not respond in time") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ApiError("API rate limit reached, please try again later") from exc
            raise ApiError(f"CheapShark API returned HTTP {status}") from exc
        except httpx.HTTPError as exc:
            raise ApiError(f"Network error while contacting CheapShark: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("CheapShark API returned invalid JSON") from exc


# ---------------------------------------------------------------------- parsing

def _to_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"Invalid numeric value for {field!r}: {value!r}") from exc


def _to_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"Invalid integer value for {field!r}: {value!r}") from exc


def _parse_search_result(item: dict[str, Any]) -> GameSearchResult:
    try:
        return GameSearchResult(
            game_id=_to_int(item["gameID"], "gameID"),
            title=str(item["external"]),
            cheapest_price=_to_float(item["cheapest"], "cheapest"),
        )
    except KeyError as exc:
        raise ApiError(f"Missing field in search result: {exc}") from exc


def _parse_deal(item: dict[str, Any]) -> Deal:
    try:
        return Deal(
            store_id=_to_int(item["storeID"], "storeID"),
            price=_to_float(item["price"], "price"),
            retail_price=_to_float(item["retailPrice"], "retailPrice"),
            savings_percent=round(_to_float(item["savings"], "savings"), 2),
        )
    except KeyError as exc:
        raise ApiError(f"Missing field in deal: {exc}") from exc


def _parse_game_details(game_id: int, data: dict[str, Any]) -> GameDetails:
    try:
        title = str(data["info"]["title"])
        deals = tuple(_parse_deal(item) for item in data.get("deals", []))
    except (KeyError, TypeError) as exc:
        raise ApiError(f"Missing field in game details: {exc}") from exc

    cheapest_ever = data.get("cheapestPriceEver") or {}
    ever_price = cheapest_ever.get("price")
    ever_date = cheapest_ever.get("date")
    return GameDetails(
        game_id=game_id,
        title=title,
        deals=deals,
        cheapest_ever_price=_to_float(ever_price, "cheapestPriceEver.price")
        if ever_price is not None
        else None,
        cheapest_ever_date=datetime.fromtimestamp(_to_int(ever_date, "date"), tz=timezone.utc)
        if ever_date is not None
        else None,
    )


def _parse_store(item: dict[str, Any]) -> Store:
    try:
        return Store(
            store_id=_to_int(item["storeID"], "storeID"),
            name=str(item["storeName"]),
            is_active=bool(int(item.get("isActive", 0))),
        )
    except KeyError as exc:
        raise ApiError(f"Missing field in store: {exc}") from exc
