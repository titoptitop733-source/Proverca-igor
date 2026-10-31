"""Exchange rates from the Frankfurter API (European Central Bank reference rates).

CheapShark reports prices in USD. Rates are cached in memory, so the API is called at most
once per `ttl`. When the API is unavailable the last known rates (or None) are returned
and the application keeps working in USD.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

import httpx

from game_tracker.models import ExchangeRates
from game_tracker.storage import utc_now

logger = logging.getLogger(__name__)


class ExchangeRateProvider:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        ttl: timedelta = timedelta(hours=12),
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url, timeout=timeout, transport=transport, follow_redirects=True
        )
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()  # web requests are served from several threads
        self._cached: ExchangeRates | None = None
        self._fetched_at: datetime | None = None

    def close(self) -> None:
        self._client.close()

    def get_rates(
        self, base: str = "USD", symbols: Sequence[str] = ("EUR", "GBP")
    ) -> ExchangeRates | None:
        with self._lock:
            now = self._clock()
            if self._cached and self._fetched_at and now - self._fetched_at < self._ttl:
                return self._cached
            try:
                self._cached = self._fetch(base, symbols)
                self._fetched_at = now
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                logger.warning("Exchange rates unavailable, using %s: %s",
                               "cached rates" if self._cached else "USD only", exc)
            return self._cached

    def _fetch(self, base: str, symbols: Sequence[str]) -> ExchangeRates:
        response = self._client.get("latest", params={"from": base, "to": ",".join(symbols)})
        response.raise_for_status()
        data = response.json()
        rates = {code: float(value) for code, value in data["rates"].items()}
        if any(rate <= 0 for rate in rates.values()):
            raise ValueError("Exchange rates must be positive")
        return ExchangeRates(base=str(data["base"]), rates=rates, date=str(data["date"]))
