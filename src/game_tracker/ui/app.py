"""Main window of the desktop application."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Literal

from game_tracker.api_client import CheapSharkClient
from game_tracker.collector import UpdateReport
from game_tracker.config import ConfigError, load_settings
from game_tracker.overview import GameOverview
from game_tracker.service import TrackerService
from game_tracker.ui.background import BackgroundRunner
from game_tracker.ui.chart_panel import ChartPanel
from game_tracker.ui.errors import show_error
from game_tracker.ui.formatting import (
    VERDICT_COLORS,
    alert_message,
    detail_lines,
    update_summary,
    wishlist_row,
)
from game_tracker.ui.search_dialog import SearchDialog

WISHLIST_COLUMNS: dict[str, tuple[str, int, Literal["w", "e", "center"]]] = {
    "title": ("Title", 240, "w"),
    "best": ("Best now", 80, "e"),
    "target": ("Target", 70, "e"),
    "low": ("Low ever", 80, "e"),
    "advice": ("Advice", 105, "center"),
}


class GameTrackerApp(tk.Tk):
    def __init__(self, service: TrackerService, auto_update: bool = True) -> None:
        super().__init__()
        self.title("Game Price Tracker")
        self.geometry("1180x680")
        self.minsize(900, 520)

        self._service = service
        self._runner = BackgroundRunner(self)
        self._status = tk.StringVar(value="Ready")
        self._selected_id: int | None = None

        self._build_toolbar()
        self._build_body()
        ttk.Label(self, textvariable=self._status, anchor="w", padding=(10, 4)).pack(
            side="bottom", fill="x"
        )
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.refresh_wishlist()
        if auto_update:
            # The snapshot interval prevents unnecessary requests on every start.
            self.after(500, self.update_prices)

    # ------------------------------------------------------------------ layout

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(side="top", fill="x")
        self._buttons = [
            ttk.Button(bar, text="Search & add…", command=self.open_search),
            ttk.Button(bar, text="Set target…", command=self.set_target),
            ttk.Button(bar, text="Remove", command=self.remove_selected),
            ttk.Button(bar, text="Update prices", command=self.update_prices),
            ttk.Button(bar, text="Force update", command=lambda: self.update_prices(force=True)),
        ]
        for button in self._buttons:
            button.pack(side="left", padx=(0, 6))

    def _build_body(self) -> None:
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10)

        left = ttk.Frame(paned)
        self._tree = ttk.Treeview(
            left, columns=list(WISHLIST_COLUMNS), show="headings", selectmode="browse"
        )
        for key, (heading, width, anchor) in WISHLIST_COLUMNS.items():
            self._tree.heading(key, text=heading)
            self._tree.column(key, width=width, anchor=anchor, stretch=key == "title")
        for verdict, color in VERDICT_COLORS.items():
            self._tree.tag_configure(verdict.name, foreground=color)
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        paned.add(left, weight=2)

        right = ttk.Frame(paned, padding=(12, 0, 0, 0))
        self._title = ttk.Label(right, text="No game selected", font=("Segoe UI", 14, "bold"))
        self._title.pack(anchor="w")
        self._verdict = tk.Label(right, text="", font=("Segoe UI", 12, "bold"), anchor="w")
        self._verdict.pack(anchor="w", pady=(4, 0))
        self._reasons = ttk.Label(right, text="", wraplength=520, justify="left")
        self._reasons.pack(anchor="w", pady=(2, 8))
        self._details = ttk.Frame(right)
        self._details.pack(anchor="w", fill="x")
        self._chart = ChartPanel(right)
        self._chart.pack(fill="both", expand=True, pady=(8, 0))
        paned.add(right, weight=3)

    # ------------------------------------------------------------------ data

    def refresh_wishlist(self, select_id: int | None = None) -> None:
        try:
            overviews = self._service.wishlist()
        except Exception as exc:  # noqa: BLE001 - shown to the user, not ignored
            show_error(self, exc)
            return
        self._tree.delete(*self._tree.get_children())
        for overview in overviews:
            self._tree.insert(
                "", "end", iid=str(overview.item.game_id), values=wishlist_row(overview),
                tags=(overview.advice.verdict.name,),
            )
        target = select_id or self._selected_id
        if target is not None and self._tree.exists(str(target)):
            self._tree.selection_set(str(target))
            self._tree.see(str(target))
        elif not overviews:
            self._show_details(None)
            self._status.set("Wishlist is empty - click 'Search & add…' to add games.")

    def _on_select(self, _event: tk.Event | None = None) -> None:
        selection = self._tree.selection()
        self._selected_id = int(selection[0]) if selection else None
        overview = self._service.game_overview(self._selected_id) if self._selected_id else None
        self._show_details(overview)

    def _show_details(self, overview: GameOverview | None) -> None:
        for child in self._details.winfo_children():
            child.destroy()
        if overview is None:
            self._title.configure(text="No game selected")
            self._verdict.configure(text="")
            self._reasons.configure(text="")
            self._chart.show_message("Select a game to see its price history")
            return

        verdict = overview.advice.verdict
        self._title.configure(text=overview.item.title)
        self._verdict.configure(text=verdict.value, fg=VERDICT_COLORS[verdict])
        self._reasons.configure(text="\n".join(f"• {r}" for r in overview.advice.reasons))
        for row, (label, value) in enumerate(detail_lines(overview)):
            ttk.Label(self._details, text=f"{label}:", foreground="gray").grid(
                row=row, column=0, sticky="w", padx=(0, 12)
            )
            ttk.Label(self._details, text=value).grid(row=row, column=1, sticky="w")
        self._chart.show(overview)

    # ------------------------------------------------------------------ actions

    def _set_busy(self, busy: bool, message: str) -> None:
        for button in self._buttons:
            button.configure(state="disabled" if busy else "normal")
        self._status.set(message)
        self.configure(cursor="watch" if busy else "")

    def open_search(self) -> None:
        SearchDialog(self, self._service, self._runner, on_added=self._game_added)

    def _game_added(self, game_id: int) -> None:
        self.refresh_wishlist(select_id=game_id)
        self._status.set("Game added to wishlist.")

    def _require_selection(self) -> int | None:
        if self._selected_id is None:
            messagebox.showinfo("No game selected", "Select a game in the list first.", parent=self)
        return self._selected_id

    def set_target(self) -> None:
        game_id = self._require_selection()
        if game_id is None:
            return
        price = simpledialog.askfloat(
            "Target price", "Notify me when the price drops to (USD):",
            parent=self, minvalue=0,
        )
        if price is None:
            return
        self._service.set_target_price(game_id, price)
        self.refresh_wishlist()
        self._on_select()

    def remove_selected(self) -> None:
        game_id = self._require_selection()
        if game_id is None:
            return
        title = self._tree.item(str(game_id), "values")[0]
        if not messagebox.askyesno(
            "Remove game", f"Remove '{title}' and its price history?", parent=self
        ):
            return
        self._service.remove_game(game_id)
        self._selected_id = None
        self.refresh_wishlist()
        self._show_details(None)
        self._status.set(f"Removed '{title}'.")

    def update_prices(self, force: bool = False) -> None:
        self._set_busy(True, "Updating prices…")
        self._runner.submit(
            lambda: self._service.update_prices(force=force), self._prices_updated, self._failed
        )

    def _prices_updated(self, report: UpdateReport) -> None:
        self._set_busy(False, update_summary(report))
        self.refresh_wishlist()
        self._on_select()
        if report.failed:
            details = "\n".join(f"Game {gid}: {reason}" for gid, reason in report.failed.items())
            messagebox.showwarning("Some games failed to update", details, parent=self)
        if report.alerts:
            self.bell()
            messagebox.showinfo("Price alert!", alert_message(report), parent=self)

    def _failed(self, error: BaseException) -> None:
        self._set_busy(False, "Last operation failed.")
        show_error(self, error)

    def _on_close(self) -> None:
        self._runner.shutdown()
        self.destroy()


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    with CheapSharkClient(settings.api_base_url, settings.http_timeout) as client:
        app = GameTrackerApp(TrackerService(client, settings))
        app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
