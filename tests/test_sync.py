import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from game_tracker.config import Settings
from game_tracker.models import Deal, GameDetails, Store
from game_tracker.storage import Storage
from game_tracker.sync import (
    SyncError,
    WishlistEntry,
    apply_wishlist,
    download_database,
    export_wishlist,
    merge_remote_database,
    read_wishlist_file,
    sync_from_cloud,
)
from tests.test_collector import FakeSource

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def game(game_id: int, price: float = 10.0) -> GameDetails:
    return GameDetails(game_id, f"Game {game_id}", (Deal(1, price, 20.0, 50.0),),
                       cheapest_ever_price=5.0, steam_app_id=100 + game_id)


# ---------------------------------------------------------------------- wishlist file

def test_export_and_read_round_trip(storage, tmp_path):
    storage.add_game(1, "Hollow Knight", target_price=7.5)
    storage.add_game(2, "Celeste")
    path = tmp_path / "data" / "wishlist.json"

    assert export_wishlist(storage, path) == 2
    entries = read_wishlist_file(path)

    assert entries == [WishlistEntry(2, "Celeste", None), WishlistEntry(1, "Hollow Knight", 7.5)]


@pytest.mark.parametrize("content", ["not json", '{"version": 99, "games": []}',
                                     '{"version": 1, "games": [{"game_id": -1}]}',
                                     '{"version": 1, "games": [{"title": "no id"}]}'])
def test_invalid_wishlist_file_is_rejected(tmp_path, content):
    path = tmp_path / "wishlist.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SyncError):
        read_wishlist_file(path)


def test_missing_wishlist_file_explains_what_to_do(tmp_path):
    with pytest.raises(SyncError, match="sync --push"):
        read_wishlist_file(tmp_path / "missing.json")


# ---------------------------------------------------------------------- cloud side

def test_apply_wishlist_adds_removes_and_retargets(storage):
    storage.add_game(1, "Game 1", target_price=5.0)   # stays, new target
    storage.add_game(3, "Game 3")                     # not in file -> removed
    source = FakeSource({1: game(1), 2: game(2)}, failing={4})
    entries = [WishlistEntry(1, "Game 1", 8.0), WishlistEntry(2, "Game 2", None),
               WishlistEntry(4, "Broken", None)]

    report = apply_wishlist(source, storage, entries)

    assert report.added == [2]
    assert report.removed == [3]
    assert report.retargeted == [1]
    assert 4 in report.failed
    assert {g.game_id for g in storage.list_games()} == {1, 2}
    assert storage.get_game(1).target_price == 8.0


# ---------------------------------------------------------------------- local side

def test_merge_adds_only_new_snapshots_and_is_idempotent(tmp_path):
    local = Storage(tmp_path / "local.db")
    remote = Storage(tmp_path / "remote.db")
    for db in (local, remote):
        db.add_game(1, "Game 1")
    remote.add_game(2, "Only in cloud")
    remote.save_stores([Store(1, "Steam", True)])
    remote.set_cheapest_ever(1, 3.0)
    remote.set_game_media(1, 367520, None)

    shared = T0
    local.record_prices(1, [Deal(1, 10.0, 20.0, 50.0)], shared)
    remote.record_prices(1, [Deal(1, 10.0, 20.0, 50.0)], shared)            # duplicate
    remote.record_prices(1, [Deal(1, 8.0, 20.0, 60.0)], T0 + timedelta(hours=6))
    remote.record_prices(2, [Deal(1, 1.0, 2.0, 50.0)], T0)

    first = merge_remote_database(local, remote)
    second = merge_remote_database(local, remote)

    assert first.rows_added == 1 and first.games == 1
    assert second.rows_added == 0                       # running again changes nothing
    assert [p.price for p in local.get_best_price_history(1)] == [10.0, 8.0]
    assert local.get_game(2) is None                    # cloud-only game is not imported
    assert local.get_game(1).cheapest_ever_price == 3.0
    assert local.get_game(1).steam_app_id == 367520
    assert local.list_stores()[0].name == "Steam"
    local.close()
    remote.close()


def test_merge_keeps_local_only_snapshots(tmp_path):
    local = Storage(tmp_path / "local.db")
    remote = Storage(tmp_path / "remote.db")
    for db in (local, remote):
        db.add_game(1, "Game 1")
    local.record_prices(1, [Deal(1, 9.0, 20.0, 55.0)], T0)
    remote.record_prices(1, [Deal(1, 12.0, 20.0, 40.0)], T0 + timedelta(days=1))

    merge_remote_database(local, remote)

    assert len(local.get_history(1)) == 2
    local.close()
    remote.close()


# ---------------------------------------------------------------------- download

def sqlite_bytes(tmp_path) -> bytes:
    path = tmp_path / "cloud.db"
    with Storage(path) as db:
        db.add_game(1, "Game 1")
        db.record_prices(1, [Deal(1, 7.0, 20.0, 65.0)], T0)
    return path.read_bytes()


def test_download_rejects_non_database(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=b"<html>oops</html>"))
    with pytest.raises(SyncError, match="not an SQLite"):
        download_database("https://raw.example.test/db", tmp_path / "x.db", transport=transport)


def test_download_404_explains_first_run(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    with pytest.raises(SyncError, match="workflow"):
        download_database("https://raw.example.test/db", tmp_path / "x.db", transport=transport)


def test_download_sends_token_for_private_repositories(tmp_path):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, content=sqlite_bytes(tmp_path))

    download_database("https://raw.example.test/db", tmp_path / "x.db", token="secret",
                      transport=httpx.MockTransport(handler))
    assert seen["auth"] == "Bearer secret"


def test_sync_from_cloud_end_to_end(tmp_path):
    content = sqlite_bytes(tmp_path)
    settings = Settings("x", tmp_path / "data" / "local.db", tmp_path, 1, 6, "WARNING",
                        sync_repo="owner/repo")
    with Storage(settings.db_path) as local:
        local.add_game(1, "Game 1")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/owner/repo/data/game_tracker.db"
        return httpx.Response(200, content=content)

    report = sync_from_cloud(settings, transport=httpx.MockTransport(handler))

    assert report.rows_added == 1
    wishlist = json.loads((tmp_path / "data" / "wishlist.json").read_text(encoding="utf-8"))
    assert wishlist["games"][0]["game_id"] == 1


def test_sync_requires_configuration(tmp_path):
    settings = Settings("x", tmp_path / "db.sqlite", tmp_path, 1, 6, "WARNING")
    with pytest.raises(SyncError, match="GT_SYNC_REPO"):
        sync_from_cloud(settings)
    assert replace(settings, sync_repo="a/b").sync_repo == "a/b"
