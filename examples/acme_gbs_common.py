"""
Shared utilities for ACME GBS example scripts.

These helpers encapsulate the recurring logic from the official
"Guideline – ACME Global Benchmark Series [GBS] (v3.04 – 01 July 2024)"
documents:

* Large & Mid Cap size-bucket selection using cumulative free-float caps
* Quarterly first-Wednesday rebalancing cadence (Section 2.2)
* Convenience printers for audit tables and calendars
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from indexmaker import Constituent, Currency, RebalancingSchedule

# Buffers derived from Section 2.1.3 (Large & Mid Cap bucket)
GENERAL_THRESHOLD: Final[float] = 0.85
TOP_BUFFER: Final[float] = 0.80
BOTTOM_BUFFER: Final[float] = 0.90

# Quarterly cadence from Section 2.2 (first Wednesday in Feb/May/Aug/Nov)
REBALANCE_MONTHS: Final[list[int]] = [2, 5, 8, 11]


@dataclass(slots=True)
class SampleSecurity:
    """
    Input blueprint for demo constituents.

    Attributes mirror the minimum data required by the guideline:
        ticker, name, country, sector, market cap, free-float %, ADV, currency.
    """

    ticker: str
    name: str
    country: str
    sector: str
    market_cap: float
    free_float: float
    average_daily_volume: float
    currency: Currency | None = None


@dataclass(slots=True)
class BucketSelection:
    """Outcome of the cumulative free-float size bucket routine."""

    selected: list[Constituent]
    audit_rows: list[dict]
    coverage: float


def build_constituents(samples: Sequence[SampleSecurity]) -> list[Constituent]:
    """Convert high-level sample definitions into Constituent objects."""

    constituents: list[Constituent] = []
    for sample in samples:
        currency = sample.currency or Currency.USD
        free_float_cap = sample.market_cap * sample.free_float
        constituents.append(
            Constituent(
                ticker=sample.ticker,
                name=sample.name,
                sector=sample.sector,
                country=sample.country,
                market_cap=sample.market_cap,
                free_float_factor=sample.free_float,
                free_float_market_cap=free_float_cap,
                average_daily_volume=sample.average_daily_volume,
                currency=currency,
            )
        )
    return constituents


def select_large_mid_bucket(
    constituents: Sequence[Constituent],
    *,
    general_threshold: float = GENERAL_THRESHOLD,
    top_buffer: float = TOP_BUFFER,
    bottom_buffer: float = BOTTOM_BUFFER,
    current_members: Iterable[str] | None = None,
) -> BucketSelection:
    """
    Apply the Large & Mid Cap bucket logic from Section 2.1.3.

    Args:
        constituents: Eligible names sorted later by free-float market cap.
        general_threshold: Minimum cumulative coverage (default 85%).
        top_buffer: Entry buffer for new names (default 80%).
        bottom_buffer: Exit buffer for incumbents (default 90%).
        current_members: Optional tickers already in the index.
    """

    total_ff = sum(
        c.free_float_market_cap if c.free_float_market_cap else c.market_cap for c in constituents
    )
    if total_ff <= 0:
        raise ValueError("Total free-float market cap must be positive.")

    ranked = sorted(
        constituents, key=lambda c: c.free_float_market_cap or c.market_cap, reverse=True
    )
    current = set(current_members or [])

    selected: list[Constituent] = []
    audit_rows: list[dict] = []
    selected_share = 0.0
    cumulative = 0.0
    row_lookup: dict[str, dict] = {}

    for c in ranked:
        ff = c.free_float_market_cap or c.market_cap
        share = ff / total_ff
        cumulative += share

        buffer_limit = bottom_buffer if c.ticker in current else top_buffer
        include = cumulative <= buffer_limit or cumulative <= general_threshold
        reason = "buffer" if cumulative <= buffer_limit else "threshold"

        if include:
            selected.append(c)
            selected_share += share

        row = {
            "ticker": c.ticker,
            "name": c.name,
            "country": c.country,
            "sector": c.sector,
            "free_float_cap": ff,
            "cumulative_share": cumulative,
            "selected": include,
            "reason": reason if include else "",
        }
        audit_rows.append(row)
        row_lookup[c.ticker] = row

    coverage = selected_share
    if coverage < general_threshold:
        for c in ranked:
            if c in selected:
                continue
            ff = c.free_float_market_cap or c.market_cap
            share = ff / total_ff
            selected.append(c)
            coverage += share
            lookup = row_lookup[c.ticker]
            lookup["selected"] = True
            lookup["reason"] = "coverage"
            if coverage >= general_threshold:
                break

    return BucketSelection(selected=selected, audit_rows=audit_rows, coverage=coverage)


def gbs_rebalancing_schedule(
    *,
    months: Sequence[int] = REBALANCE_MONTHS,
    selection_offset: int = 7,
    announcement_offset: int = 3,
) -> RebalancingSchedule:
    """Quarterly schedule aligned with the first Wednesday rule from Section 2.2."""

    # Use day=1 placeholder; the scripts log the actual first Wednesday separately.
    return (
        RebalancingSchedule.builder()
        .frequency("quarterly")
        .on_months(list(months))
        .on_day(1)
        .selection_date_offset(selection_offset)
        .announcement_date_offset(announcement_offset)
        .build()
    )


def first_wednesday(year: int, month: int) -> date:
    """Compute the first Wednesday of a given month."""

    anchor = date(year, month, 1)
    offset = (2 - anchor.weekday()) % 7  # Wednesday == 2
    return anchor + timedelta(days=offset)


def upcoming_rebalances(
    *,
    start_year: int,
    months: Sequence[int] = REBALANCE_MONTHS,
    cycles: int = 4,
) -> list[date]:
    """Return the next `cycles` first-Wednesday dates from the given start year."""

    today = date.today()
    results: list[date] = []
    year = start_year

    while len(results) < cycles:
        for month in months:
            candidate = first_wednesday(year, month)
            if candidate < today:
                continue
            results.append(candidate)
            if len(results) >= cycles:
                break
        year += 1

    return results


def print_rebalance_calendar(
    *,
    start_year: int,
    months: Sequence[int] = REBALANCE_MONTHS,
    cycles: int = 4,
) -> None:
    """Pretty-print the next few first-Wednesday rebalance dates."""

    for scheduled in upcoming_rebalances(start_year=start_year, months=months, cycles=cycles):
        print(f"  • {scheduled:%Y-%m-%d} (first Wednesday of {scheduled:%B})")


def print_selection_audit(audit_rows: Sequence[dict]) -> None:
    """Render the cumulative free-float coverage table."""

    print("\nCUMULATIVE FREE-FLOAT COVERAGE")
    print("-" * 72)
    print(
        f"{'Ticker':<6} {'Country':<15} {'FF Cap ($B)':>12} "
        f"{'Cum %':>8} {'Selected':>9}  Reason"
    )
    for row in audit_rows:
        ff_cap_b = row["free_float_cap"] / 1_000_000_000
        cum_pct = row["cumulative_share"] * 100
        selected = "Yes" if row["selected"] else "No"
        print(
            f"{row['ticker']:<6} {row['country']:<15} {ff_cap_b:>12.1f} "
            f"{cum_pct:>8.2f} {selected:>9}  {row['reason']}"
        )
