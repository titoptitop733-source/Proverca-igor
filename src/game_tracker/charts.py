"""Price history charts rendered with matplotlib.

The chart is drawn onto a matplotlib `Figure` (not pyplot), so the same drawing code is
used both for saving PNG files (CLI) and for embedding in the Tkinter GUI.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from game_tracker.analysis import to_frame
from game_tracker.models import PricePoint


def draw_price_history(
    ax: Axes,
    best_points: Sequence[PricePoint],
    title: str,
    target_price: float | None = None,
    all_time_low: float | None = None,
) -> None:
    """Draw best price over time onto existing axes."""
    frame = to_frame(best_points)
    if frame.empty:
        raise ValueError("There is no price history to plot yet")

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
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"${value:g}"))
    if len(frame) == 1:
        # A single snapshot would otherwise produce an x axis spanning several years.
        moment = frame["recorded_at"].iloc[0]
        ax.set_xlim(moment - timedelta(days=1), moment + timedelta(days=1))
    ax.grid(alpha=0.3)
    ax.legend(fontsize="small")
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")


def plot_price_history(
    best_points: Sequence[PricePoint],
    title: str,
    output_path: Path,
    target_price: float | None = None,
    all_time_low: float | None = None,
) -> Path:
    """Save a chart of the best price over time to `output_path` (PNG)."""
    figure = Figure(figsize=(10, 5))
    draw_price_history(figure.add_subplot(), best_points, title, target_price, all_time_low)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=120)
    return output_path
