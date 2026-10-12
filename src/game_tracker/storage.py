"""SQLite persistence for the wishlist, stores and price history."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from game_tracker.models import Deal, PricePoint, Store, WishlistItem

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (
    store_id   INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS games (
    game_id             INTEGER PRIMARY KEY,
    title               TEXT NOT NULL,
    target_price        REAL CHECK (target_price IS NULL OR target_price >= 0),
    added_at            TEXT NOT NULL,
    cheapest_ever_price REAL
);

CREATE TABLE IF NOT EXISTS price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    store_id        INTEGER NOT NULL,
    price           REAL NOT NULL CHECK (price >= 0),
    retail_price    REAL NOT NULL CHECK (retail_price >= 0),
    savings_percent REAL NOT NULL,
    recorded_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_game_time
    ON price_history (game_id, recorded_at);
"""

# Columns added after the first released version (v0.1.0). Databases created by older
# versions are upgraded automatically when the application starts.
MIGRATIONS: dict[str, dict[str, str]] = {
    "games": {"cheapest_ever_price": "REAL"},
}

_PRICE_POINT_COLUMNS = """
    h.game_id, h.store_id, s.name AS store_name, h.price,
    h.retail_price, h.savings_percent, h.recorded_at
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Storage:
    """Repository over a SQLite database. All queries are parameterized."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._migrate()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Storage:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _migrate(self) -> None:
        for table, columns in MIGRATIONS.items():
            existing = {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}
            for column, column_type in columns.items():
                if column not in existing:
                    logger.info("Migrating database: adding %s.%s", table, column)
                    # Table/column names come from the constant above, never from user input.
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        self._conn.commit()

    # ------------------------------------------------------------------ stores

    def save_stores(self, stores: Iterable[Store]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO stores (store_id, name, is_active) VALUES (?, ?, ?)
                ON CONFLICT(store_id) DO UPDATE SET
                    name = excluded.name, is_active = excluded.is_active
                """,
                [(s.store_id, s.name, int(s.is_active)) for s in stores],
            )

    # ------------------------------------------------------------------ wishlist

    def add_game(self, game_id: int, title: str, target_price: float | None = None) -> bool:
        """Add a game to the wishlist. Returns False if it is already there."""
        _validate_price(target_price, "Target price")
        with self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO games (game_id, title, target_price, added_at) "
                "VALUES (?, ?, ?, ?)",
                (game_id, title, target_price, utc_now().isoformat()),
            )
        return cursor.rowcount == 1

    def set_target_price(self, game_id: int, target_price: float | None) -> bool:
        _validate_price(target_price, "Target price")
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE games SET target_price = ? WHERE game_id = ?",
                (target_price, game_id),
            )
        return cursor.rowcount == 1

    def set_cheapest_ever(self, game_id: int, price: float | None) -> None:
        """Store the all-time lowest price reported by the API."""
        _validate_price(price, "Cheapest price")
        if price is None:
            return
        with self._conn:
            self._conn.execute(
                "UPDATE games SET cheapest_ever_price = ? WHERE game_id = ?",
                (price, game_id),
            )

    def remove_game(self, game_id: int) -> bool:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
        return cursor.rowcount == 1

    def get_game(self, game_id: int) -> WishlistItem | None:
        row = self._conn.execute(
            "SELECT game_id, title, target_price, added_at, cheapest_ever_price "
            "FROM games WHERE game_id = ?",
            (game_id,),
        ).fetchone()
        return _row_to_wishlist_item(row) if row else None

    def list_games(self) -> list[WishlistItem]:
        rows = self._conn.execute(
            "SELECT game_id, title, target_price, added_at, cheapest_ever_price "
            "FROM games ORDER BY title"
        ).fetchall()
        return [_row_to_wishlist_item(row) for row in rows]

    # ------------------------------------------------------------------ prices

    def record_prices(
        self, game_id: int, deals: Iterable[Deal], recorded_at: datetime | None = None
    ) -> int:
        """Store a snapshot of all current deals for a game. Returns rows inserted."""
        timestamp = (recorded_at or utc_now()).isoformat()
        rows = [
            (game_id, d.store_id, d.price, d.retail_price, d.savings_percent, timestamp)
            for d in deals
        ]
        with self._conn:
            self._conn.executemany(
                "INSERT INTO price_history "
                "(game_id, store_id, price, retail_price, savings_percent, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def last_snapshot_at(self, game_id: int) -> datetime | None:
        row = self._conn.execute(
            "SELECT MAX(recorded_at) AS last FROM price_history WHERE game_id = ?",
            (game_id,),
        ).fetchone()
        return datetime.fromisoformat(row["last"]) if row and row["last"] else None

    def get_history(self, game_id: int) -> list[PricePoint]:
        """All recorded deals (every store, every snapshot)."""
        rows = self._conn.execute(
            f"""
            SELECT {_PRICE_POINT_COLUMNS}
            FROM price_history h
            LEFT JOIN stores s ON s.store_id = h.store_id
            WHERE h.game_id = ?
            ORDER BY h.recorded_at, h.price
            """,
            (game_id,),
        ).fetchall()
        return [_row_to_price_point(row) for row in rows]

    def get_best_price_history(self, game_id: int) -> list[PricePoint]:
        """The cheapest deal of every snapshot - one row per snapshot."""
        rows = self._conn.execute(
            f"""
            SELECT {_PRICE_POINT_COLUMNS}
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY recorded_at ORDER BY price, store_id
                ) AS rank_in_snapshot
                FROM price_history
                WHERE game_id = ?
            ) h
            LEFT JOIN stores s ON s.store_id = h.store_id
            WHERE h.rank_in_snapshot = 1
            ORDER BY h.recorded_at
            """,
            (game_id,),
        ).fetchall()
        return [_row_to_price_point(row) for row in rows]

    def latest_best_price(self, game_id: int) -> PricePoint | None:
        """Cheapest deal from the most recent snapshot of a game."""
        history = self.get_best_price_history(game_id)
        return history[-1] if history else None


def _validate_price(price: float | None, label: str) -> None:
    if price is not None and price < 0:
        raise ValueError(f"{label} must not be negative")


def _row_to_wishlist_item(row: sqlite3.Row) -> WishlistItem:
    return WishlistItem(
        game_id=row["game_id"],
        title=row["title"],
        target_price=row["target_price"],
        added_at=datetime.fromisoformat(row["added_at"]),
        cheapest_ever_price=row["cheapest_ever_price"],
    )


def _row_to_price_point(row: sqlite3.Row) -> PricePoint:
    return PricePoint(
        game_id=row["game_id"],
        store_id=row["store_id"],
        store_name=row["store_name"],
        price=row["price"],
        retail_price=row["retail_price"],
        savings_percent=row["savings_percent"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
    )
