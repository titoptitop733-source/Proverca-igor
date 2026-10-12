from datetime import datetime, timezone

import pytest

from game_tracker.models import Deal, Store


def test_add_and_list_games(storage):
    assert storage.add_game(612, "LEGO Batman", target_price=5.0) is True
    games = storage.list_games()
    assert len(games) == 1
    assert games[0].title == "LEGO Batman"
    assert games[0].target_price == 5.0


def test_adding_duplicate_returns_false(storage):
    storage.add_game(612, "LEGO Batman")
    assert storage.add_game(612, "LEGO Batman") is False


def test_negative_target_price_is_rejected(storage):
    with pytest.raises(ValueError):
        storage.add_game(612, "LEGO Batman", target_price=-1)


def test_title_with_sql_characters_is_stored_safely(storage):
    title = "Robert'); DROP TABLE games;--"
    storage.add_game(1, title)
    assert storage.get_game(1).title == title


def test_record_prices_and_history_with_store_names(storage):
    storage.save_stores([Store(1, "Steam", True)])
    storage.add_game(612, "LEGO Batman")
    deals = [Deal(1, 19.99, 19.99, 0.0), Deal(25, 3.99, 19.99, 80.0)]

    inserted = storage.record_prices(612, deals)

    history = storage.get_history(612)
    assert inserted == 2
    assert len(history) == 2
    assert history[0].price == 3.99  # ordered by price within one snapshot
    assert history[0].store_name is None  # store 25 not synced -> LEFT JOIN
    assert history[1].store_name == "Steam"


def test_latest_best_price_uses_most_recent_snapshot(storage):
    storage.add_game(612, "LEGO Batman")
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = datetime(2026, 2, 1, tzinfo=timezone.utc)
    storage.record_prices(612, [Deal(1, 2.00, 20.0, 90.0)], recorded_at=old)
    storage.record_prices(612, [Deal(1, 15.0, 20.0, 25.0), Deal(2, 12.0, 20.0, 40.0)],
                          recorded_at=new)

    best = storage.latest_best_price(612)

    assert best is not None
    assert best.price == 12.0
    assert best.recorded_at == new


def test_remove_game_deletes_its_history(storage):
    storage.add_game(612, "LEGO Batman")
    storage.record_prices(612, [Deal(1, 5.0, 10.0, 50.0)])

    assert storage.remove_game(612) is True
    assert storage.get_history(612) == []
    assert storage.remove_game(612) is False


def test_set_target_price(storage):
    storage.add_game(612, "LEGO Batman")
    assert storage.set_target_price(612, 4.5) is True
    assert storage.get_game(612).target_price == 4.5
    assert storage.set_target_price(999, 4.5) is False
