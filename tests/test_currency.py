from datetime import datetime, timedelta, timezone

import httpx

from game_tracker.currency import ExchangeRateProvider

RESPONSE = {"amount": 1.0, "base": "USD", "date": "2026-10-09", "rates": {"EUR": 0.86, "GBP": 0.75}}


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 12, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now


def provider(handler, clock=None) -> ExchangeRateProvider:
    return ExchangeRateProvider("https://fx.example.test/v1",
                                transport=httpx.MockTransport(handler), clock=clock or Clock())


def test_rates_are_parsed():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["from"] == "USD"
        return httpx.Response(200, json=RESPONSE)

    rates = provider(handler).get_rates()
    assert rates.rates["EUR"] == 0.86
    assert rates.date == "2026-10-09"


def test_rates_are_cached_until_ttl_expires():
    calls = []
    clock = Clock()

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=RESPONSE)

    fx = provider(handler, clock)
    fx.get_rates()
    fx.get_rates()
    assert len(calls) == 1
    clock.now += timedelta(hours=13)
    fx.get_rates()
    assert len(calls) == 2


def test_failure_returns_none_without_cache():
    assert provider(lambda r: httpx.Response(503)).get_rates() is None


def test_failure_keeps_last_known_rates():
    responses = iter([httpx.Response(200, json=RESPONSE), httpx.Response(500)])
    clock = Clock()
    fx = provider(lambda r: next(responses), clock)
    first = fx.get_rates()
    clock.now += timedelta(days=1)
    assert fx.get_rates() == first


def test_invalid_rates_are_rejected():
    bad = {**RESPONSE, "rates": {"EUR": -1}}
    assert provider(lambda r: httpx.Response(200, json=bad)).get_rates() is None
