"""Command-line interface (MVP user interface)."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable

from game_tracker.api_client import ApiError, CheapSharkClient
from game_tracker.collector import sync_stores, update_wishlist
from game_tracker.config import ConfigError, load_settings
from game_tracker.storage import Storage

Handler = Callable[[argparse.Namespace, CheapSharkClient, Storage], int]


def _money(value: float | None) -> str:
    return "-" if value is None else f"${value:.2f}"


def _non_negative_float(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a number") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return value


# ---------------------------------------------------------------------- commands

def cmd_search(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    results = client.search_games(args.title, limit=args.limit)
    if not results:
        print(f"No games found for {args.title!r}.")
        return 0
    print(f"{'ID':>8}  {'Cheapest':>9}  Title")
    for game in results:
        print(f"{game.game_id:>8}  {_money(game.cheapest_price):>9}  {game.title}")
    print("\nAdd a game with: game-tracker add <ID> [--target PRICE]")
    return 0


def cmd_add(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    details = client.get_game(args.game_id)  # validates that the game exists
    if not storage.add_game(details.game_id, details.title, args.target):
        print(f"'{details.title}' is already in your wishlist.")
        return 0
    sync_stores(client, storage)
    storage.record_prices(details.game_id, details.deals)
    best = details.best_deal
    print(f"Added '{details.title}' to wishlist.")
    if best:
        print(f"Current best price: {_money(best.price)} (-{best.savings_percent:.0f}%)")
    print(f"Cheapest price ever: {_money(details.cheapest_ever_price)}")
    return 0


def cmd_remove(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    if storage.remove_game(args.game_id):
        print(f"Game {args.game_id} removed from wishlist.")
        return 0
    print(f"Game {args.game_id} is not in your wishlist.", file=sys.stderr)
    return 1


def cmd_target(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    if storage.set_target_price(args.game_id, args.price):
        print(f"Target price for game {args.game_id} set to {_money(args.price)}.")
        return 0
    print(f"Game {args.game_id} is not in your wishlist.", file=sys.stderr)
    return 1


def cmd_list(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    games = storage.list_games()
    if not games:
        print("Wishlist is empty. Use 'search' and 'add' to add games.")
        return 0
    print(f"{'ID':>8}  {'Best now':>9}  {'Target':>8}  {'Store':<16} Title")
    for game in games:
        best = storage.latest_best_price(game.game_id)
        price = _money(best.price) if best else "-"
        store = (best.store_name or f"#{best.store_id}") if best else "-"
        print(
            f"{game.game_id:>8}  {price:>9}  {_money(game.target_price):>8}  "
            f"{store:<16} {game.title}"
        )
    return 0


def cmd_update(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    sync_stores(client, storage)
    report = update_wishlist(client, storage)
    print(f"Updated {len(report.updated)} game(s).")
    for game_id, reason in report.failed.items():
        print(f"  ! game {game_id}: {reason}", file=sys.stderr)
    for alert in report.alerts:
        print(
            f"  *** PRICE ALERT: '{alert.title}' is {_money(alert.price)} "
            f"(your target {_money(alert.target_price)})"
        )
    return 1 if report.failed and not report.updated else 0


def cmd_history(args: argparse.Namespace, client: CheapSharkClient, storage: Storage) -> int:
    game = storage.get_game(args.game_id)
    if game is None:
        print(f"Game {args.game_id} is not in your wishlist.", file=sys.stderr)
        return 1
    history = storage.get_history(args.game_id)
    print(f"Price history for '{game.title}' ({len(history)} records)")
    print(f"{'Recorded (UTC)':<17}  {'Price':>8}  {'Retail':>8}  {'Off':>4}  Store")
    for point in history:
        print(
            f"{point.recorded_at:%Y-%m-%d %H:%M}  {_money(point.price):>8}  "
            f"{_money(point.retail_price):>8}  {point.savings_percent:>3.0f}%  "
            f"{point.store_name or '#' + str(point.store_id)}"
        )
    return 0


# ---------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="game-tracker", description="Track PC game prices using the CheapShark API."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="search games by title")
    p.add_argument("title")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(handler=cmd_search)

    p = sub.add_parser("add", help="add a game to the wishlist")
    p.add_argument("game_id", type=int)
    p.add_argument("--target", type=_non_negative_float, help="alert when price drops to this")
    p.set_defaults(handler=cmd_add)

    p = sub.add_parser("remove", help="remove a game from the wishlist")
    p.add_argument("game_id", type=int)
    p.set_defaults(handler=cmd_remove)

    p = sub.add_parser("target", help="set target price for a wishlist game")
    p.add_argument("game_id", type=int)
    p.add_argument("price", type=_non_negative_float)
    p.set_defaults(handler=cmd_target)

    p = sub.add_parser("list", help="show wishlist with latest prices")
    p.set_defaults(handler=cmd_list)

    p = sub.add_parser("update", help="fetch current prices for all wishlist games")
    p.set_defaults(handler=cmd_update)

    p = sub.add_parser("history", help="show recorded price history of a game")
    p.add_argument("game_id", type=int)
    p.set_defaults(handler=cmd_history)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    handler: Handler = args.handler
    try:
        with CheapSharkClient(settings.api_base_url, settings.http_timeout) as client, Storage(
            settings.db_path
        ) as storage:
            return handler(args, client, storage)
    except ApiError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
