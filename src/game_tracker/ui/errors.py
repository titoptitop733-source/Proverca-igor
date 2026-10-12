"""Turning exceptions into user-friendly dialogs."""

from __future__ import annotations

import logging
from tkinter import messagebox

import tkinter as tk

from game_tracker.api_client import ApiError

logger = logging.getLogger(__name__)


def show_error(parent: tk.Misc, error: BaseException) -> None:
    if isinstance(error, ApiError):
        messagebox.showerror("Connection problem", str(error), parent=parent)
    elif isinstance(error, ValueError):
        messagebox.showerror("Invalid input", str(error), parent=parent)
    else:
        logger.error("Unexpected error", exc_info=error)
        messagebox.showerror(
            "Unexpected error", f"Something went wrong: {error}\nSee the log for details.",
            parent=parent,
        )
