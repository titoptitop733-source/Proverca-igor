"""Run slow work (HTTP requests) outside the Tkinter main loop.

Tkinter widgets may only be touched from the main thread, so the result of a background
task is collected by polling with `after()` and callbacks run in the main thread.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar

import tkinter as tk

T = TypeVar("T")


class BackgroundRunner:
    def __init__(self, root: tk.Misc, poll_ms: int = 100) -> None:
        self._root = root
        self._poll_ms = poll_ms
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gt-worker")

    def submit(
        self,
        task: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        future = self._executor.submit(task)
        self._root.after(self._poll_ms, self._poll, future, on_success, on_error)

    def _poll(
        self,
        future: Future[T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        if not future.done():
            self._root.after(self._poll_ms, self._poll, future, on_success, on_error)
            return
        error = future.exception()
        if error is not None:
            on_error(error)
        else:
            on_success(future.result())

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
