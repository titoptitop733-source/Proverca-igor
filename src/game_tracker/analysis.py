"""Price statistics and the "buy now or wait" recommendation (pandas)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from enum import Enum

import pandas as pd

from game_tracker.models import PricePoint

# Tunable thresholds of the recommendation heuristic.
NEAR_LOW_TOLERANCE = 0.10          # within 10 % of the all-time low -> buy
GOOD_DISCOUNT_PERCENT = 50.0       # at least 50 % off -> good deal
BELOW_AVERAGE_RATIO = 0.85         # 15 % below own average price -> good deal
CHEAPER_BEFORE_RATIO = 0.70        # was 30 %+ cheaper before -> worth waiting
MIN_SNAPSHOTS_FOR_CONFIDENCE = 3


class Verdict(str, Enum):
    BUY_NOW = "BUY NOW"
    GOOD_DEAL = "GOOD DEAL"
    WAIT = "WAIT"
    NO_DATA = "NO DATA"


@dataclass(frozen=True)
class PriceStats:
    snapshots: int
    first_seen: datetime
    last_seen: datetime
    current_price: float
    current_store: str
    retail_price: float
    current_discount: float
    observed_min: float
    observed_max: float
    average_price: float
    all_time_low: float
    discount_share: float          # fraction of snapshots with any discount (0..1)
    max_discount: float
    last_discount_at: datetime | None


@dataclass(frozen=True)
class Recommendation:
    verdict: Verdict
    reasons: tuple[str, ...]


def to_frame(points: Sequence[PricePoint]) -> pd.DataFrame:
    """Convert price points to a DataFrame sorted by time."""
    columns = [f.name for f in fields(PricePoint)]
    if not points:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame([asdict(p) for p in points], columns=columns)
    frame["recorded_at"] = pd.to_datetime(frame["recorded_at"], utc=True)
    return frame.sort_values("recorded_at").reset_index(drop=True)


def compute_stats(
    best_points: Sequence[PricePoint], cheapest_ever: float | None = None
) -> PriceStats | None:
    """Compute statistics from the best price of each snapshot.

    `cheapest_ever` is the all-time low reported by the API; it covers the period
    before we started collecting our own history.
    """
    frame = to_frame(best_points)
    if frame.empty:
        return None

    latest = frame.iloc[-1]
    discounted = frame[frame["savings_percent"] > 0]
    observed_min = float(frame["price"].min())
    all_time_low = observed_min if cheapest_ever is None else min(observed_min, cheapest_ever)

    return PriceStats(
        snapshots=len(frame),
        first_seen=frame["recorded_at"].iloc[0].to_pydatetime(),
        last_seen=latest["recorded_at"].to_pydatetime(),
        current_price=float(latest["price"]),
        current_store=latest["store_name"] or f"store #{latest['store_id']}",
        retail_price=float(latest["retail_price"]),
        current_discount=float(latest["savings_percent"]),
        observed_min=observed_min,
        observed_max=float(frame["price"].max()),
        average_price=round(float(frame["price"].mean()), 2),
        all_time_low=all_time_low,
        discount_share=len(discounted) / len(frame),
        max_discount=float(frame["savings_percent"].max()),
        last_discount_at=discounted["recorded_at"].iloc[-1].to_pydatetime()
        if not discounted.empty
        else None,
    )


def recommend(stats: PriceStats | None, target_price: float | None = None) -> Recommendation:
    """Decide whether to buy now or wait, with human-readable reasons."""
    if stats is None:
        return Recommendation(Verdict.NO_DATA, ("No price snapshots recorded yet.",))

    price = stats.current_price
    low = stats.all_time_low
    notes: list[str] = []
    if stats.snapshots < MIN_SNAPSHOTS_FOR_CONFIDENCE:
        notes.append(f"Only {stats.snapshots} snapshot(s) collected - confidence is low.")

    if target_price is not None and price <= target_price:
        return Recommendation(
            Verdict.BUY_NOW,
            (f"Price ${price:.2f} reached your target ${target_price:.2f}.", *notes),
        )

    if price <= low * (1 + NEAR_LOW_TOLERANCE):
        return Recommendation(
            Verdict.BUY_NOW,
            (f"Price ${price:.2f} is within {NEAR_LOW_TOLERANCE:.0%} "
             f"of the all-time low ${low:.2f}.", *notes),
        )

    below_average = (
        stats.snapshots >= MIN_SNAPSHOTS_FOR_CONFIDENCE
        and price <= stats.average_price * BELOW_AVERAGE_RATIO
    )
    if stats.current_discount >= GOOD_DISCOUNT_PERCENT or below_average:
        reason = (
            f"{stats.current_discount:.0f}% off right now."
            if stats.current_discount >= GOOD_DISCOUNT_PERCENT
            else f"Price is below the average ${stats.average_price:.2f}."
        )
        return Recommendation(
            Verdict.GOOD_DEAL,
            (reason, f"But the all-time low was ${low:.2f}.", *notes),
        )

    if low <= price * CHEAPER_BEFORE_RATIO:
        cheaper_by = (1 - low / price) * 100 if price else 0
        return Recommendation(
            Verdict.WAIT,
            (f"It has already been {cheaper_by:.0f}% cheaper (${low:.2f}); "
             "a sale is likely to come again.", *notes),
        )

    return Recommendation(
        Verdict.WAIT,
        ("No significant discount right now and the price is close to its usual level.",
         *notes),
    )
