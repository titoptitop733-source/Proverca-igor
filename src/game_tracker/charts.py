"""Price history charts rendered with matplotlib."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files, no GUI window needed

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from game_tracker.analysis import to_frame  # noqa: E402
from game_tracker.models import PricePoint  # noqa: E402


def plot_price_history(
    best_points: Sequence[PricePoint],
    title: str,
    output_path: Path,
    target_price: float | None = None,
    all_time_low: float | None = None,
) -> Path:
    """Save a chart of the best price over time to `output_path` (PNG)."""
    frame = to_frame(best_points)
    if frame.empty:
        raise ValueError("There is no price history to plot yet")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.step(frame["recorded_at"], frame["price"], where="post", marker="o",
            linewidth=2, label="Best price")
    ax.plot(frame["recorded_at"], frame["retail_price"], linestyle=":",
            color="gray", label="Retail price")
    if target_price is not None:
        ax.axhline(target_price, color="green", linestyle="--",
                   label=f"Your target (${target_price:.2f})")
    if all_time_low is not None:
        ax.axhline(all_time_low, color="red", linestyle="--", alpha=0.6,
                   label=f"All-time low (${all_time_low:.2f})")

    ax.set_title(f"Price history: {title}")
    ax.set_ylabel("Price (USD)")
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"${value:.0f}"))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output_path
