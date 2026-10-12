"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from game_tracker.analysis import compute_stats, recommend
from game_tracker.api_client import ApiError, CheapSharkClient
from game_tracker.charts import plot_price_history
from game_tracker.collector import save_snapshot, sync_stores, update_wishlist
from game_tracker.config import ConfigError, Settings, load_settings
from game_tracker.models import PricePoint
from game_tracker.storage import Storage


@dataclass(frozen=True)
class AppContext:
    client: CheapSharkClient
    storage: Storage
    settings: Settings


Handler = Callable[[argparse.Namespace, AppContext], int]


def _money(value: float | None) -> str:
    return "-" if value is None else f"${value:.2f}"


def _store(point: PricePoint) -> str:
    return point.store_name or f"#{point.store_id}"


def _non_negative_float(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a number") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return value


def _not_in_wishlist(game_id: int) -> int:
    print(f"Game {game_id} is not in your wishlist.", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------- commands

def cmd_search(args: argparse.Namespace, ctx: AppContext) -> int:
    results = ctx.client.search_games(args.title, limit=args.limit)
    if not results:
        print(f"No games found for {args.title!r}.")
        return 0
    print(f"{'ID':>8}  {'Cheapest':>9}  Title")
    for game in results:
        print(f"{game.game_id:>8}  {_money(game.cheapest_price):>9}  {game.title}")
    print("\nAdd a game with: game-tracker add <ID> [--target PRICE]")
    return 0


def cmd_add(args: argparse.Namespace, ctx: AppContext) -> int:
    details = ctx.client.get_game(args.game_id)  # validates that the game exists
    if not ctx.storage.add_game(details.game_id, details.title, args.target):
        print(f"'{details.title}' is already in your wishlist.")
        return 0
    sync_stores(ctx.client, ctx.storage)
    save_snapshot(ctx.storage, details)
    best = details.best_deal
    print(f"Added '{details.title}' to wishlist.")
    if best:
        print(f"Current best price: {_money(best.price)} (-{best.savings_percent:.0f}%)")
    print(f"Cheapest price ever: {_money(details.cheapest_ever_price)}")
    return 0


def cmd_remove(args: argparse.Namespace, ctx: AppContext) -> int:
    if ctx.storage.remove_game(args.game_id):
        print(f"Game {args.game_id} removed from wishlist.")
        return 0
    return _not_in_wishlist(args.game_id)


def cmd_target(args: argparse.Namespace, ctx: AppContext) -> int:
    if ctx.storage.set_target_price(args.game_id, args.price):
        print(f"Target price for game {args.game_id} set to {_money(args.price)}.")
        return 0
    return _not_in_wishlist(args.game_id)


def cmd_list(args: argparse.Namespace, ctx: AppContext) -> int:
    games = ctx.storage.list_games()
    if not games:
        print("Wishlist is empty. Use 'search' and 'add' to add games.")
        return 0
    print(f"{'ID':>8}  {'Best now':>9}  {'Target':>8}  {'Low ever':>9}  {'Advice':<10} Title")
    for game in games:
        history = ctx.storage.get_best_price_history(game.game_id)
        stats = compute_stats(history, game.cheapest_ever_price)
        advice = recommend(stats, game.target_price).verdict.value
        price = _money(stats.current_price) if stats else "-"
        low = _money(stats.all_time_low) if stats else "-"
        print(
            f"{game.game_id:>8}  {price:>9}  {_money(game.target_price):>8}  "
            f"{low:>9}  {advice:<10} {game.title}"
        )
    return 0


def cmd_update(args: argparse.Namespace, ctx: AppContext) -> int:
    sync_stores(ctx.client, ctx.storage)
    interval = timedelta(hours=ctx.settings.min_snapshot_interval_hours)
    report = update_wishlist(ctx.client, ctx.storage, min_interval=interval, force=args.force)
    print(f"Updated {len(report.updated)} game(s).")
    if report.skipped:
        print(
            f"Skipped {len(report.skipped)} game(s) updated less than "
            f"{ctx.settings.min_snapshot_interval_hours:g} h ago (use --force to override)."
        )
    for game_id, reason in report.failed.items():
        print(f"  ! game {game_id}: {reason}", file=sys.stderr)
    for alert in report.alerts:
        print(
            f"  *** PRICE ALERT: '{alert.title}' is {_money(alert.price)} "
            f"(your target {_money(alert.target_price)})"
        )
    return 1 if report.failed and not report.updated else 0


def cmd_history(args: argparse.Namespace, ctx: AppContext) -> int:
    game = ctx.storage.get_game(args.game_id)
    if game is None:
        return _not_in_wishlist(args.game_id)
    if args.all:
        history = ctx.storage.get_history(args.game_id)
        label = "all stores"
    else:
        history = ctx.storage.get_best_price_history(args.game_id)
        label = "best price per snapshot"
    print(f"Price history for '{game.title}' - {label} ({len(history)} records)")
    print(f"{'Recorded (UTC)':<17}  {'Price':>8}  {'Retail':>8}  {'Off':>4}  Store")
    for point in history:
        print(
            f"{point.recorded_at:%Y-%m-%d %H:%M}  {_money(point.price):>8}  "
            f"{_money(point.retail_price):>8}  {point.savings_percent:>3.0f}%  {_store(point)}"
        )
    return 0


def cmd_stats(args: argparse.Namespace, ctx: AppContext) -> int:
    game = ctx.storage.get_game(args.game_id)
    if game is None:
        return _not_in_wishlist(args.game_id)
    stats = compute_stats(
        ctx.storage.get_best_price_history(args.game_id), game.cheapest_ever_price
    )
    advice = recommend(stats, game.target_price)

    print(f"=== {game.title} ===")
    if stats:
        print(f"Current best price : {_money(stats.current_price)} at {stats.current_store} "
              f"(-{stats.current_discount:.0f}%, retail {_money(stats.retail_price)})")
        print(f"All-time low       : {_money(stats.all_time_low)}")
        print(f"Observed range     : {_money(stats.observed_min)} - {_money(stats.observed_max)}"
              f", average {_money(stats.average_price)}")
        print(f"Discounted in      : {stats.discount_share:.0%} of {stats.snapshots} snapshot(s),"
              f" biggest discount {stats.max_discount:.0f}%")
        last = f"{stats.last_discount_at:%Y-%m-%d}" if stats.last_discount_at else "never seen"
        print(f"Last discount seen : {last}")
        print(f"Tracking since     : {stats.first_seen:%Y-%m-%d}")
    print(f"Your target        : {_money(game.target_price)}")
    print(f"\nRecommendation: {advice.verdict.value}")
    for reason in advice.reasons:
        print(f"  - {reason}")
    return 0


def cmd_chart(args: argparse.Namespace, ctx: AppContext) -> int:
    game = ctx.storage.get_game(args.game_id)
    if game is None:
        return _not_in_wishlist(args.game_id)
    history = ctx.storage.get_best_price_history(args.game_id)
    stats = compute_stats(history, game.cheapest_ever_price)
    output: Path = args.output or ctx.settings.charts_dir / f"game_{game.game_id}.png"
    path = plot_price_history(
        history,
        game.title,
        output,
        target_price=game.target_price,
        all_time_low=stats.all_time_low if stats else None,
    )
    print(f"Chart saved to {path.resolve()}")
    if args.open:
        webbrowser.open(path.resolve().as_uri())
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

    p = sub.add_parser("list", help="show wishlist with prices and advice")
    p.set_defaults(handler=cmd_list)

    p = sub.add_parser("update", help="fetch current prices for all wishlist games")
    p.add_argument("--force", action="store_true", help="ignore minimal snapshot interval")
    p.set_defaults(handler=cmd_update)

    p = sub.add_parser("history", help="show recorded price history of a game")
    p.add_argument("game_id", type=int)
    p.add_argument("--all", action="store_true", help="show every store, not only the best")
    p.set_defaults(handler=cmd_history)

    p = sub.add_parser("stats", help="price statistics and buy/wait recommendation")
    p.add_argument("game_id", type=int)
    p.set_defaults(handler=cmd_stats)

    p = sub.add_parser("chart", help="save a price history chart as PNG")
    p.add_argument("game_id", type=int)
    p.add_argument("--output", type=Path, help="output PNG path")
    p.add_argument("--open", action="store_true", help="open the chart after saving")
    p.set_defaults(handler=cmd_chart)

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
            return handler(args, AppContext(client, storage, settings))
    except ApiError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"File system error: {exc}", file=sys.stderr)
        return 1
