import pytest

from game_tracker.charts import plot_price_history
from tests.test_analysis import series


def test_chart_is_saved_as_png(tmp_path):
    output = tmp_path / "charts" / "game.png"

    path = plot_price_history(series([20, 10, 15]), "Test game", output,
                              target_price=12, all_time_low=8)

    assert path.exists()
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_chart_without_data_raises(tmp_path):
    with pytest.raises(ValueError):
        plot_price_history([], "Empty", tmp_path / "x.png")
