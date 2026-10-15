"""Cloud price collection with GitHub Actions.

The cloud collector (.github/workflows/collect-prices.yml) checks prices every few hours
and stores its database on the `data` branch of the repository. This module provides:

* the wishlist file `data/wishlist.json` - the list of games the cloud should track,
* `apply_wishlist`  - used in the cloud: makes the database match the wishlist file,
* `sync_from_cloud` - used locally: downloads the cloud database and merges new price
  snapshots into the local one. Nothing local is overwritten or deleted.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from game_tracker.api_client import ApiError
from game_tracker.collector import GameDataSource, add_to_wishlist
from game_tracker.config import Settings
from game_tracker.storage import Storage

logger = logging.getLogger(__name__)

WISHLIST_FILE_VERSION = 1
DEFAULT_WISHLIST_FILE = Path("data/wishlist.json")
MAX_DATABASE_BYTES = 50 * 1024 * 1024


class SyncError(Exception):
    """Raised when cloud synchronisation cannot be completed."""


@dataclass(frozen=True)
class WishlistEntry:
    game_id: int
    title: str
    target_price: float | None


@dataclass
class ApplyReport:
    added: list[int] = field(default_factory=list)
    removed: list[int] = field(default_factory=list)
    retargeted: list[int] = field(default_factory=list)
    failed: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeReport:
    games: int
    rows_added: int


# ---------------------------------------------------------------------- wishlist file

def export_wishlist(storage: Storage, path: Path = DEFAULT_WISHLIST_FILE) -> int:
    """Write the tracked games and targets to a JSON file. Returns the number of games."""
    games = [
        {"game_id": g.game_id, "title": g.title, "target_price": g.target_price}
        for g in storage.list_games()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": WISHLIST_FILE_VERSION, "games": games}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(games)


def read_wishlist_file(path: Path) -> list[WishlistEntry]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SyncError(
            f"Wishlist file {path} does not exist - run 'game-tracker sync --push' locally first"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SyncError(f"Wishlist file {path} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or data.get("version") != WISHLIST_FILE_VERSION:
        raise SyncError(f"Unsupported wishlist file format in {path}")
    entries = []
    for item in data.get("games", []):
        try:
            game_id = int(item["game_id"])
            target = item.get("target_price")
            target = None if target is None else float(target)
        except (KeyError, TypeError, ValueError) as exc:
            raise SyncError(f"Invalid game entry in {path}: {item!r}") from exc
        if game_id <= 0 or (target is not None and target < 0):
            raise SyncError(f"Invalid game entry in {path}: {item!r}")
        entries.append(WishlistEntry(game_id, str(item.get("title", "")), target))
    return entries


def apply_wishlist(
    source: GameDataSource, storage: Storage, entries: list[WishlistEntry]
) -> ApplyReport:
    """Make the database track exactly the games from the wishlist file (cloud side)."""
    report = ApplyReport()
    wanted = {entry.game_id: entry for entry in entries}
    current = {item.game_id: item for item in storage.list_games()}

    for game_id in current.keys() - wanted.keys():
        storage.remove_game(game_id)
        report.removed.append(game_id)

    for game_id, entry in wanted.items():
        if game_id not in current:
            try:
                add_to_wishlist(source, storage, game_id, entry.target_price)
                report.added.append(game_id)
            except ApiError as exc:
                report.failed[game_id] = str(exc)
        elif current[game_id].target_price != entry.target_price:
            storage.set_target_price(game_id, entry.target_price)
            report.retargeted.append(game_id)
    return report


def push_wishlist(path: Path = DEFAULT_WISHLIST_FILE) -> str:
    """Commit and push the wishlist file with git, so the cloud collector sees changes."""
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=60)

    try:
        git("add", str(path)).check_returncode()
        if git("diff", "--cached", "--quiet", "--", str(path)).returncode == 0:
            return "Wishlist file is unchanged - nothing to push."
        message = "Update tracked games for the cloud collector"
        git("commit", "-m", message, "--", str(path)).check_returncode()
        pushed = git("push", "origin", "HEAD")
    except FileNotFoundError as exc:
        raise SyncError("git is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise SyncError(f"git failed: {exc.stderr or exc.stdout}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError("git did not finish in time") from exc
    if pushed.returncode != 0:
        raise SyncError(f"git push failed: {pushed.stderr.strip()}")
    return "Wishlist file committed and pushed."


# ---------------------------------------------------------------------- cloud database

def wishlist_path(settings: Settings) -> Path:
    """wishlist.json lives next to the database (data/ by default)."""
    return settings.db_path.parent / "wishlist.json"


def cloud_database_url(repo: str, branch: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/game_tracker.db"


def download_database(
    url: str, destination: Path, timeout: float = 30.0, token: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Path:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=timeout, transport=transport, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise SyncError(f"Could not download the cloud database: {exc}") from exc
    if response.status_code == 404:
        raise SyncError("Cloud database not found - has the GitHub workflow run at least once?")
    if response.status_code != 200:
        raise SyncError(f"Cloud database download failed with HTTP {response.status_code}")
    if len(response.content) > MAX_DATABASE_BYTES:
        raise SyncError("Cloud database is unexpectedly large")
    if not response.content.startswith(b"SQLite format 3\x00"):
        raise SyncError("Downloaded file is not an SQLite database")
    destination.write_bytes(response.content)
    return destination


def merge_remote_database(local: Storage, remote: Storage) -> MergeReport:
    """Copy price snapshots the local database does not have yet (for locally tracked games)."""
    local.save_stores(remote.list_stores())
    games = 0
    added = 0
    for item in local.list_games():
        remote_item = remote.get_game(item.game_id)
        if remote_item is None:
            continue
        known = local.snapshot_keys(item.game_id)
        new_points = [
            point for point in remote.get_history(item.game_id)
            if (point.recorded_at.isoformat(), point.store_id) not in known
        ]
        if new_points:
            added += local.insert_price_points(new_points)
            games += 1
        if remote_item.cheapest_ever_price is not None:
            local.set_cheapest_ever(item.game_id, remote_item.cheapest_ever_price)
        local.set_game_media(item.game_id, remote_item.steam_app_id, remote_item.thumb_url)
    return MergeReport(games=games, rows_added=added)


def sync_from_cloud(
    settings: Settings, transport: httpx.BaseTransport | None = None
) -> MergeReport:
    """Download the cloud database, merge it into the local one and refresh wishlist.json."""
    if not settings.sync_repo:
        raise SyncError("Cloud sync is not configured - set GT_SYNC_REPO in .env")
    url = cloud_database_url(settings.sync_repo, settings.sync_branch)
    with tempfile.TemporaryDirectory() as tmp:
        remote_path = download_database(
            url, Path(tmp) / "cloud.db", settings.http_timeout, settings.sync_token, transport
        )
        with Storage(settings.db_path) as local, Storage(remote_path) as remote:
            report = merge_remote_database(local, remote)
            export_wishlist(local, wishlist_path(settings))
    logger.info("Merged %d price rows for %d games from the cloud", report.rows_added, report.games)
    return report
