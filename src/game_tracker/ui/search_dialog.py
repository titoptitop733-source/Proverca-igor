"""Dialog for searching games and adding them to the wishlist."""

from __future__ import annotations

from collections.abc import Callable

import tkinter as tk
from tkinter import ttk

from game_tracker.models import GameDetails, GameSearchResult
from game_tracker.service import TrackerService
from game_tracker.ui.background import BackgroundRunner
from game_tracker.ui.errors import show_error
from game_tracker.ui.formatting import money, parse_optional_price


class SearchDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        service: TrackerService,
        runner: BackgroundRunner,
        on_added: Callable[[int], None],
    ) -> None:
        super().__init__(master)
        self.title("Search games")
        self.geometry("680x440")
        self.minsize(520, 320)
        self.transient(master)

        self._service = service
        self._runner = runner
        self._on_added = on_added

        self._query = tk.StringVar()
        self._target = tk.StringVar()
        self._status = tk.StringVar(value="Type a game title and press Enter.")
        self._build()
        self._entry.focus_set()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        self._entry = ttk.Entry(top, textvariable=self._query)
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", lambda _event: self._search())
        self._search_button = ttk.Button(top, text="Search", command=self._search)
        self._search_button.pack(side="left", padx=(8, 0))

        middle = ttk.Frame(self, padding=(10, 0))
        middle.pack(fill="both", expand=True)
        self._results = ttk.Treeview(
            middle, columns=("title", "cheapest"), show="headings", selectmode="browse"
        )
        self._results.heading("title", text="Title")
        self._results.heading("cheapest", text="Cheapest now")
        self._results.column("title", width=480)
        self._results.column("cheapest", width=110, anchor="e")
        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=self._results.yview)
        self._results.configure(yscrollcommand=scrollbar.set)
        self._results.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._results.bind("<Double-1>", lambda _event: self._add())

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Target price (optional):").pack(side="left")
        ttk.Entry(bottom, textvariable=self._target, width=10).pack(side="left", padx=6)
        self._add_button = ttk.Button(bottom, text="Add to wishlist", command=self._add)
        self._add_button.pack(side="left")
        ttk.Label(bottom, textvariable=self._status, foreground="gray").pack(
            side="left", padx=12
        )

    # ------------------------------------------------------------------ actions

    def _set_busy(self, busy: bool, message: str = "") -> None:
        state = "disabled" if busy else "normal"
        self._search_button.configure(state=state)
        self._add_button.configure(state=state)
        if message:
            self._status.set(message)

    def _search(self) -> None:
        query = self._query.get().strip()
        if not query:
            self._status.set("Please type a title first.")
            return
        self._set_busy(True, "Searching…")
        self._runner.submit(lambda: self._service.search(query), self._show_results, self._fail)

    def _show_results(self, results: list[GameSearchResult]) -> None:
        if not self.winfo_exists():
            return
        self._results.delete(*self._results.get_children())
        for game in results:
            self._results.insert(
                "", "end", iid=str(game.game_id), values=(game.title, money(game.cheapest_price))
            )
        self._set_busy(False, f"Found {len(results)} game(s). Double-click to add.")

    def _add(self) -> None:
        selection = self._results.selection()
        if not selection:
            self._status.set("Select a game in the list first.")
            return
        try:
            target = parse_optional_price(self._target.get())
        except ValueError as exc:
            show_error(self, exc)
            return
        game_id = int(selection[0])
        self._set_busy(True, "Adding…")
        self._runner.submit(
            lambda: self._service.add_game(game_id, target),
            lambda details: self._added(game_id, details),
            self._fail,
        )

    def _added(self, game_id: int, details: GameDetails | None) -> None:
        if not self.winfo_exists():
            return
        if details is None:
            self._set_busy(False, "This game is already in your wishlist.")
            return
        self._set_busy(False, f"Added '{details.title}'.")
        self._on_added(game_id)

    def _fail(self, error: BaseException) -> None:
        if not self.winfo_exists():
            return
        self._set_busy(False, "Something went wrong.")
        show_error(self, error)
