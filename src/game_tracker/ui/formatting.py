"""Pure formatting helpers for the GUI (no Tkinter here, so they are easy to test)."""

from __future__ import annotations

from game_tracker.analysis import Verdict
from game_tracker.collector import UpdateReport
from game_tracker.overview import GameOverview

VERDICT_COLORS: dict[Verdict, str] = {
    Verdict.BUY_NOW: "#1b873f",
    Verdict.GOOD_DEAL: "#1f6feb",
    Verdict.WAIT: "#9a6700",
    Verdict.NO_DATA: "#6e7781",
}


def money(value: float | None) -> str:
    return "-" if value is None else f"${value:.2f}"


def parse_optional_price(raw: str) -> float | None:
    """'' -> None, '12,5' or '12.5' -> 12.5; raises ValueError for invalid input."""
    text = raw.strip().replace(",", ".").lstrip("$")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"'{raw}' is not a valid price") from exc
    if value < 0:
        raise ValueError("Price must not be negative")
    return value


def wishlist_row(overview: GameOverview) -> tuple[str, str, str, str, str]:
    stats = overview.stats
    return (
        overview.item.title,
        money(stats.current_price) if stats else "-",
        money(overview.item.target_price),
        money(stats.all_time_low) if stats else "-",
        overview.advice.verdict.value,
    )


def detail_lines(overview: GameOverview) -> list[tuple[str, str]]:
    stats = overview.stats
    lines = [("Your target", money(overview.item.target_price))]
    if stats is None:
        return [("Status", "No price data yet"), *lines]
    last_discount = f"{stats.last_discount_at:%Y-%m-%d}" if stats.last_discount_at else "never seen"
    return [
        ("Best price now", f"{money(stats.current_price)} at {stats.current_store} "
                           f"(-{stats.current_discount:.0f}%)"),
        ("Retail price", money(stats.retail_price)),
        ("All-time low", money(stats.all_time_low)),
        ("Average (tracked)", money(stats.average_price)),
        ("Discounted in", f"{stats.discount_share:.0%} of {stats.snapshots} snapshots"),
        ("Biggest discount", f"{stats.max_discount:.0f}%"),
        ("Last discount", last_discount),
        ("Tracking since", f"{stats.first_seen:%Y-%m-%d}"),
        *lines,
    ]


def update_summary(report: UpdateReport) -> str:
    parts = [f"updated {len(report.updated)}"]
    if report.skipped:
        parts.append(f"skipped {len(report.skipped)} (recently updated)")
    if report.failed:
        parts.append(f"failed {len(report.failed)}")
    return "Prices: " + ", ".join(parts)


def alert_message(report: UpdateReport) -> str:
    return "\n".join(
        f"• {a.title}: {money(a.price)} (your target {money(a.target_price)})"
        for a in report.alerts
    )
