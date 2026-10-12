"""FastAPI application: REST API under /api and the DROPZONE frontend as static files."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from game_tracker import __version__
from game_tracker.api_client import DEAL_SORT_OPTIONS, ApiError
from game_tracker.currency import ExchangeRateProvider
from game_tracker.insights import build_dashboard
from game_tracker.service import TrackerService
from game_tracker.web import serializers
from game_tracker.web.schemas import (
    AddGameIn,
    DashboardOut,
    DealOut,
    GameDetailOut,
    GameSummaryOut,
    MetaOut,
    SearchResultOut,
    StoreOut,
    TargetIn,
    UpdateIn,
    UpdateOut,
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
MAX_QUERY_PRICE = 1_000.0

# On some Windows machines the registry maps .js to text/plain, which makes browsers refuse
# to execute JavaScript modules. Register the correct types explicitly.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def create_app(
    service: TrackerService,
    rates: ExchangeRateProvider | None = None,
    snapshot_interval_hours: float = 6.0,
) -> FastAPI:
    """Build the application. Dependencies are passed in, so tests can use fakes."""
    app = FastAPI(
        title="DROPZONE - Game Price Tracker API",
        version=__version__,
        description="Prices by CheapShark (USD), exchange rates by Frankfurter (ECB).",
    )

    # ------------------------------------------------------------------ errors

    @app.exception_handler(ApiError)
    def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        logger.warning("External API error: %s", exc)
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def require_game(game_id: int) -> GameDetailOut:
        overview = service.game_overview(game_id)
        if overview is None:
            raise HTTPException(status_code=404, detail=f"Game {game_id} is not tracked")
        return serializers.detail(overview, service.latest_offers(game_id))

    # ------------------------------------------------------------------ meta

    @app.get("/api/meta", response_model=MetaOut, tags=["meta"])
    def meta() -> MetaOut:
        info = rates.get_rates() if rates else None
        return MetaOut(
            version=__version__,
            base_currency="USD",
            rates={"USD": 1.0, **(info.rates if info else {})},
            rates_date=info.date if info else None,
            snapshot_interval_hours=snapshot_interval_hours,
            price_source="CheapShark API (cheapshark.com)",
            rates_source="Frankfurter API - European Central Bank reference rates",
        )

    # ------------------------------------------------------------------ wishlist

    @app.get("/api/dashboard", response_model=DashboardOut, tags=["wishlist"])
    def dashboard() -> DashboardOut:
        return serializers.dashboard(build_dashboard(service.wishlist()))

    @app.get("/api/wishlist", response_model=list[GameSummaryOut], tags=["wishlist"])
    def wishlist() -> list[GameSummaryOut]:
        return [serializers.summary(overview) for overview in service.wishlist()]

    @app.post("/api/wishlist", response_model=GameDetailOut,
              status_code=status.HTTP_201_CREATED, tags=["wishlist"])
    def add_game(payload: AddGameIn) -> GameDetailOut:
        if service.add_game(payload.game_id, payload.target_price) is None:
            raise HTTPException(status_code=409, detail="This game is already tracked")
        return require_game(payload.game_id)

    @app.delete("/api/wishlist/{game_id}", status_code=status.HTTP_204_NO_CONTENT,
                tags=["wishlist"])
    def remove_game(game_id: int) -> Response:
        if not service.remove_game(game_id):
            raise HTTPException(status_code=404, detail=f"Game {game_id} is not tracked")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.put("/api/wishlist/{game_id}/target", response_model=GameDetailOut, tags=["wishlist"])
    def set_target(game_id: int, payload: TargetIn) -> GameDetailOut:
        if not service.set_target_price(game_id, payload.target_price):
            raise HTTPException(status_code=404, detail=f"Game {game_id} is not tracked")
        return require_game(game_id)

    @app.get("/api/games/{game_id}", response_model=GameDetailOut, tags=["wishlist"])
    def game_detail(game_id: int) -> GameDetailOut:
        return require_game(game_id)

    @app.post("/api/update", response_model=UpdateOut, tags=["wishlist"])
    def update_prices(payload: UpdateIn | None = None) -> UpdateOut:
        return serializers.update_report(service.update_prices(force=bool(payload and payload.force)))

    # ------------------------------------------------------------------ catalogue

    @app.get("/api/search", response_model=list[SearchResultOut], tags=["catalogue"])
    def search(
        q: Annotated[str, Query(min_length=1, max_length=100)],
        limit: Annotated[int, Query(ge=1, le=60)] = 20,
    ) -> list[SearchResultOut]:
        tracked = service.tracked_ids()
        return [serializers.search_result(r, tracked) for r in service.search(q, limit=limit)]

    @app.get("/api/stores", response_model=list[StoreOut], tags=["catalogue"])
    def stores() -> list[StoreOut]:
        return serializers.stores(service.stores())

    @app.get("/api/deals", response_model=list[DealOut], tags=["catalogue"])
    def deals(
        sort: Annotated[str, Query()] = "Deal Rating",
        store: Annotated[list[int] | None, Query()] = None,
        max_price: Annotated[float | None, Query(ge=0, le=MAX_QUERY_PRICE)] = None,
        title: Annotated[str | None, Query(max_length=100)] = None,
        page: Annotated[int, Query(ge=0, le=50)] = 0,
        page_size: Annotated[int, Query(ge=1, le=60)] = 30,
    ) -> list[DealOut]:
        if sort not in DEAL_SORT_OPTIONS:
            raise HTTPException(status_code=422, detail=f"sort must be one of {DEAL_SORT_OPTIONS}")
        listings = service.deals(sort_by=sort, store_ids=store, max_price=max_price,
                                 title=title, page=page, page_size=page_size)
        names = {s.store_id: s.name for s in service.stores()}
        tracked = service.tracked_ids()
        return [serializers.deal(listing, names, tracked) for listing in listings]

    # ------------------------------------------------------------------ frontend

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
    return app

