"""
Rebalance date selection over a trading calendar.

A backtest that never rebalances is not testing the methodology the user defined,
so the simulation needs to know which of its trading days are rebalance days. Dates
are chosen from the actual observed trading days rather than from a synthetic
calendar, so a period boundary that falls on a weekend or holiday resolves to the
first trading day of that period.
"""

from __future__ import annotations

from datetime import date

from app.models.index import RebalanceFrequency

# Number of months in each rebalancing period. Daily and weekly are handled
# separately since they do not divide the year into month-aligned periods.
_MONTHS_PER_PERIOD = {
    RebalanceFrequency.MONTHLY.value: 1,
    RebalanceFrequency.QUARTERLY.value: 3,
    RebalanceFrequency.SEMI_ANNUAL.value: 6,
    RebalanceFrequency.ANNUAL.value: 12,
}


def _period_key(day: date, months: int) -> tuple[int, int]:
    """Identify which rebalancing period a date falls in."""
    return (day.year, (day.month - 1) // months)


def rebalance_dates(trading_days: list[date], frequency: str) -> set[date]:
    """
    Pick the rebalance days out of a sorted list of trading days.

    The first trading day is never a rebalance day: it is inception, where the
    holdings are established in the first place.

    An unrecognised frequency yields no rebalances rather than guessing, so a
    typo produces a buy-and-hold result that is obviously wrong instead of a
    plausible one that is subtly wrong.
    """
    if len(trading_days) < 2:
        return set()

    if frequency == RebalanceFrequency.DAILY.value:
        return set(trading_days[1:])

    if frequency == RebalanceFrequency.WEEKLY.value:
        selected = set()
        seen: set[tuple[int, int]] = set()
        for day in trading_days:
            key = day.isocalendar()[:2]  # (ISO year, ISO week)
            if key not in seen:
                seen.add(key)
                selected.add(day)
        selected.discard(trading_days[0])
        return selected

    months = _MONTHS_PER_PERIOD.get(frequency)
    if months is None:
        return set()

    selected = set()
    seen_periods: set[tuple[int, int]] = set()
    for day in trading_days:
        key = _period_key(day, months)
        if key not in seen_periods:
            seen_periods.add(key)
            selected.add(day)

    selected.discard(trading_days[0])
    return selected
