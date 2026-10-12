import pytest

from game_tracker.collector import PriceAlert, UpdateReport
from game_tracker.ui.formatting import alert_message, parse_optional_price, update_summary


@pytest.mark.parametrize(("raw", "expected"),
                         [("", None), ("  ", None), ("12.5", 12.5), ("12,5", 12.5), ("$7", 7.0)])
def test_parse_optional_price(raw, expected):
    assert parse_optional_price(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "-1", "1.2.3"])
def test_parse_optional_price_rejects_invalid(raw):
    with pytest.raises(ValueError):
        parse_optional_price(raw)


def test_update_summary_and_alerts():
    report = UpdateReport(updated=[1], skipped=[2, 3], failed={4: "boom"},
                          alerts=[PriceAlert(1, "Celeste", 1, 4.99, 5.0)])
    assert update_summary(report) == (
        "Prices: updated 1, skipped 2 (recently updated), failed 1"
    )
    assert "Celeste: $4.99 (your target $5.00)" in alert_message(report)
