"""Matplotlib chart embedded in a Tkinter frame."""

from __future__ import annotations

from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from game_tracker.charts import draw_price_history
from game_tracker.overview import GameOverview


class ChartPanel(ttk.Frame):
    def __init__(self, master: ttk.Widget) -> None:
        super().__init__(master)
        self._figure = Figure(figsize=(6, 3.6), dpi=100)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self.show_message("Select a game to see its price history")

    def show_message(self, text: str) -> None:
        self._figure.clear()
        ax = self._figure.add_subplot()
        ax.text(0.5, 0.5, text, ha="center", va="center", color="gray")
        ax.set_axis_off()
        self._canvas.draw_idle()

    def show(self, overview: GameOverview) -> None:
        if not overview.history:
            self.show_message("No price data yet")
            return
        self._figure.clear()
        draw_price_history(
            self._figure.add_subplot(),
            overview.history,
            overview.item.title,
            target_price=overview.item.target_price,
            all_time_low=overview.stats.all_time_low if overview.stats else None,
        )
        self._figure.tight_layout()
        self._canvas.draw_idle()
