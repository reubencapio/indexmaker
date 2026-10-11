"""
Index analytics: a real level history for an index, and statistics over it.

The history is a *current-composition* series: today's constituents, at today's
share counts, valued on every past trading day. That answers "how would what I
hold now have behaved?" from real prices. It is not a point-in-time simulation --
there is no rebalancing, no transaction cost and no change of membership -- and
the response says so. Backtests cover that question.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.models.index import Index
from app.services import analytics_math
from app.services.analytics_math import Point
from app.services.market_data_service import MarketDataService

DEFAULT_BENCHMARK = "SPY"

# Look-back in years for each selectable period. YTD is resolved at request time.
PERIOD_YEARS: dict[str, float] = {
    "1M": 1 / 12,
    "3M": 0.25,
    "6M": 0.5,
    "YTD": 1.0,
    "1Y": 1.0,
    "3Y": 3.0,
    "5Y": 5.0,
    "10Y": 10.0,
}

# Price history is slow to fetch and does not change intraday for daily closes.
CACHE_SECONDS = 900
_MAX_CACHE_ENTRIES = 256
_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}


class AnalyticsUnavailableError(Exception):
    """The index has no priced holdings, or no price history could be loaded."""


def period_start(period: str, today: date) -> date:
    if period == "YTD":
        # Anchor on the prior year's last close so YTD includes January's first day.
        return date(today.year - 1, 12, 31)
    return today - timedelta(days=round(PERIOD_YEARS[period] * 365.25))


def _positions(index: Index) -> dict[str, float]:
    """
    Share count per ticker for the series.

    An index that has been calculated holds explicit shares. One that has not is
    given shares implied by its weights and last prices, which reproduces the same
    portfolio the first calculation would establish.
    """
    active = [c for c in index.components if c.is_active]
    held = {c.ticker: c.shares for c in active if c.shares and c.shares > 0}
    if held:
        return held
    return {c.ticker: c.weight / c.price for c in active if c.weight and c.price and c.price > 0}


def build_level_series(
    positions: dict[str, float],
    prices: dict[str, dict[date, float]],
    anchor_level: float | None,
) -> tuple[list[Point], list[str], str | None]:
    """
    Value fixed positions across every trading day covered by all of them.

    Returns the series, the tickers left out for having no price history at all,
    and the ticker whose listing date limited how far back the series goes (if any
    did). The series starts on the first day every remaining ticker has traded:
    starting earlier would mean valuing a portfolio with holes in it.

    Gaps inside a ticker's history are forward-filled, as a holder would carry the
    last traded price. The result is rescaled so the final point equals
    `anchor_level`, tying the chart to the index's published level.
    """
    excluded = sorted(t for t in positions if not prices.get(t))
    included = {t: s for t, s in positions.items() if prices.get(t)}
    if not included:
        return [], excluded, None

    first_days = {t: min(prices[t]) for t in included}
    start = max(first_days.values())
    limiting = max(first_days, key=lambda t: first_days[t])
    if all(d == start for d in first_days.values()):
        limiting = None

    all_days = sorted({d for t in included for d in prices[t] if d >= start})
    last_price: dict[str, float] = {}
    raw: list[tuple[date, float]] = []
    for day in all_days:
        for ticker in included:
            px = prices[ticker].get(day)
            if px is not None and px > 0:
                last_price[ticker] = px
        if len(last_price) < len(included):
            continue
        raw.append((day, sum(last_price[t] * shares for t, shares in included.items())))

    if not raw or raw[-1][1] <= 0:
        return [], excluded, limiting

    scale = (anchor_level / raw[-1][1]) if anchor_level and anchor_level > 0 else 1.0
    return [Point(day, value * scale) for day, value in raw], excluded, limiting


def align(points: list[Point], other: dict[date, float]) -> list[Point] | None:
    """`other` sampled on the dates of `points`, forward-filled. None if it starts late."""
    if not other or not points:
        return None
    days = sorted(other)
    if days[0] > points[0].day:
        return None
    out: list[Point] = []
    i = 0
    current = other[days[0]]
    for p in points:
        while i < len(days) and days[i] <= p.day:
            current = other[days[i]]
            i += 1
        out.append(Point(p.day, current))
    return out


def _closes(history: list[dict[str, Any]]) -> dict[date, float]:
    out: dict[date, float] = {}
    for row in history:
        close = row.get("close")
        if close is None or close != close or close <= 0:  # NaN check
            continue
        out[date.fromisoformat(row["date"])] = float(close)
    return out


def sector_allocation(index: Index) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    for c in index.components:
        if c.is_active and c.weight:
            totals[c.sector or "Unclassified"] = (
                totals.get(c.sector or "Unclassified", 0.0) + c.weight
            )
    return [
        {"name": name, "weight": weight}
        for name, weight in sorted(totals.items(), key=lambda kv: -kv[1])
    ]


def concentration(index: Index) -> dict[str, float | int | None]:
    weights = sorted((c.weight for c in index.components if c.is_active and c.weight), reverse=True)
    if not weights:
        return {"top_5_weight": None, "top_10_weight": None, "effective_holdings": None, "count": 0}
    hhi = sum(w * w for w in weights)
    return {
        "top_5_weight": sum(weights[:5]),
        "top_10_weight": sum(weights[:10]),
        # Inverse Herfindahl: the number of equal-weighted names that would be as
        # concentrated as this index. 50 names with an effective count of 8 is
        # really an 8-stock portfolio.
        "effective_holdings": 1.0 / hhi if hhi > 0 else None,
        "count": len(weights),
    }


async def compute_index_analytics(
    index: Index,
    period: str,
    benchmark_ticker: str = DEFAULT_BENCHMARK,
    market_data: MarketDataService | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """
    Level history and statistics for `index` over `period`.

    Raises:
        AnalyticsUnavailableError: if there is nothing to value or no prices came back.
    """
    today = today or datetime.now(timezone.utc).date()
    cache_key = (index.id, period, benchmark_ticker, index.last_calculated, index.divisor, today)
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    positions = _positions(index)
    if not positions:
        raise AnalyticsUnavailableError(
            "This index has no priced constituents yet. Calculate it first."
        )

    start = period_start(period, today)
    service = market_data or MarketDataService()
    tickers = sorted(set(positions) | {benchmark_ticker})
    history = await service.get_prices_for_tickers(
        tickers,
        # A few days of slack so the first point is a close on or before `start`.
        datetime.combine(start - timedelta(days=7), datetime.min.time()),
        datetime.combine(today + timedelta(days=1), datetime.min.time()),
    )
    prices = {t: _closes(history.get(t, [])) for t in tickers}

    points, excluded, limiting = build_level_series(
        positions,
        {t: prices[t] for t in positions},
        index.current_value,
    )
    # Begin at the last close on or before `start`, so the first return measured
    # is the first day of the period rather than a stray day from the slack.
    anchor = max((i for i, p in enumerate(points) if p.day <= start), default=0)
    points = points[anchor:]
    if len(points) < 2:
        raise AnalyticsUnavailableError(
            "No price history is available for this index's constituents right now."
        )

    benchmark_points = align(points, prices.get(benchmark_ticker, {}))
    stats = analytics_math.summarize(points, benchmark_points)

    # Rebase the benchmark to the index's first value so both lines share an axis.
    benchmark_series: list[float] | None = None
    if benchmark_points:
        base = benchmark_points[0].value
        benchmark_series = [points[0].value * b.value / base for b in benchmark_points]

    drawdowns = analytics_math.drawdown_series([p.value for p in points])
    trailing = {
        label: analytics_math.trailing_return(points, period_start(label, today))
        for label in ("1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y")
        if PERIOD_YEARS[label] <= PERIOD_YEARS[period] or label == period
    }

    requested_days = (today - start).days
    covered_days = (points[-1].day - points[0].day).days

    result: dict[str, Any] = {
        "index_id": index.id,
        "period": period,
        "methodology": "current_composition",
        "as_of": points[-1].day.isoformat(),
        "start_date": points[0].day.isoformat(),
        "requested_start_date": start.isoformat(),
        # True when a late-listed constituent shortened the window noticeably.
        "history_truncated": covered_days < requested_days * 0.9,
        "limited_by": limiting,
        "excluded_tickers": excluded,
        "benchmark": benchmark_ticker if benchmark_points else None,
        "series": [
            {
                "date": p.day.isoformat(),
                "value": round(p.value, 4),
                "benchmark": round(benchmark_series[i], 4) if benchmark_series else None,
                "drawdown": round(drawdowns[i], 6),
            }
            for i, p in enumerate(points)
        ],
        "stats": stats,
        "trailing_returns": trailing,
        "monthly_returns": analytics_math.monthly_returns(points),
        "sector_allocation": sector_allocation(index),
        "concentration": concentration(index),
    }

    if len(_cache) >= _MAX_CACHE_ENTRIES:
        _cache.clear()
    _cache[cache_key] = (time.monotonic(), result)
    return result
