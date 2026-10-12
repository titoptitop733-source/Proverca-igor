from datetime import datetime, timedelta, timezone

import pytest

from game_tracker.analysis import Verdict, compute_stats, recommend, to_frame
from game_tracker.models import PricePoint

START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def series(prices: list[float], retail: float = 20.0) -> list[PricePoint]:
    """Daily best-price snapshots with given prices."""
    return [
        PricePoint(
            game_id=1, store_id=1, store_name="Steam", price=price, retail_price=retail,
            savings_percent=round((1 - price / retail) * 100, 2),
            recorded_at=START + timedelta(days=i),
        )
        for i, price in enumerate(prices)
    ]


def test_to_frame_handles_empty_input():
    assert to_frame([]).empty


def test_compute_stats_basic_values():
    stats = compute_stats(series([20, 20, 10, 20]))

    assert stats is not None
    assert stats.snapshots == 4
    assert stats.current_price == 20
    assert stats.observed_min == 10
    assert stats.observed_max == 20
    assert stats.average_price == pytest.approx(17.5)
    assert stats.discount_share == pytest.approx(0.25)
    assert stats.max_discount == pytest.approx(50)
    assert stats.last_discount_at == START + timedelta(days=2)


def test_api_all_time_low_is_used_when_lower_than_observed():
    stats = compute_stats(series([20, 20]), cheapest_ever=4.99)
    assert stats.all_time_low == 4.99
    assert stats.observed_min == 20


def test_no_data_verdict():
    assert recommend(None).verdict is Verdict.NO_DATA


def test_target_reached_means_buy():
    stats = compute_stats(series([20, 9]), cheapest_ever=5)
    assert recommend(stats, target_price=10).verdict is Verdict.BUY_NOW


def test_near_all_time_low_means_buy():
    stats = compute_stats(series([20, 20, 5.4]), cheapest_ever=5)
    advice = recommend(stats)
    assert advice.verdict is Verdict.BUY_NOW
    assert "all-time low" in advice.reasons[0]


def test_big_discount_is_good_deal_but_not_lowest():
    stats = compute_stats(series([20, 20, 9]), cheapest_ever=3)
    assert recommend(stats).verdict is Verdict.GOOD_DEAL


def test_full_price_with_much_cheaper_history_means_wait():
    stats = compute_stats(series([20, 20, 20]), cheapest_ever=5)
    advice = recommend(stats)
    assert advice.verdict is Verdict.WAIT
    assert "75% cheaper" in advice.reasons[0]


def test_low_confidence_note_with_few_snapshots():
    stats = compute_stats(series([20]), cheapest_ever=5)
    assert any("confidence" in reason for reason in recommend(stats).reasons)


def test_free_game_does_not_crash():
    stats = compute_stats(series([0.0]), cheapest_ever=0.0)
    assert recommend(stats).verdict is Verdict.BUY_NOW
