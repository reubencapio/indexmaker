"""
Performance and risk statistics for an index level series.

Pure functions over dated values, with no database or network access, so every
number shown on the analytics page can be checked by a unit test. Conventions are
stated where they matter, because two reasonable definitions of the same statistic
routinely differ by enough to mislead:

- Returns are simple daily returns of the level series.
- Volatility is the sample standard deviation of daily returns, annualised by
  sqrt(252).
- Annualised return is a CAGR over calendar time, not mean daily return * 252.
- Drawdowns are reported as negative fractions (-0.25 is a 25% fall from a peak).
- A statistic that cannot be computed from the data is None, never zero: a missing
  Sharpe ratio and a Sharpe ratio of 0.00 mean different things.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

TRADING_DAYS_PER_YEAR = 252
DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Point:
    day: date
    value: float


def daily_returns(values: list[float]) -> list[float]:
    """Simple period-over-period returns. One fewer element than `values`."""
    return [values[i] / values[i - 1] - 1.0 for i in range(1, len(values)) if values[i - 1] > 0]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _sample_std(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def total_return(values: list[float]) -> float | None:
    if len(values) < 2 or values[0] <= 0:
        return None
    return values[-1] / values[0] - 1.0


def annualized_return(points: list[Point]) -> float | None:
    """
    CAGR over the calendar span of the series.

    None for spans under 30 days: annualising a fortnight's return produces a
    number that is arithmetically valid and practically meaningless.
    """
    if len(points) < 2 or points[0].value <= 0:
        return None
    days = (points[-1].day - points[0].day).days
    if days < 30:
        return None
    growth = points[-1].value / points[0].value
    if growth <= 0:
        return None
    return growth ** (DAYS_PER_YEAR / days) - 1.0


def annualized_volatility(returns: list[float]) -> float | None:
    std = _sample_std(returns)
    return None if std is None else std * math.sqrt(TRADING_DAYS_PER_YEAR)


def downside_deviation(returns: list[float], target: float = 0.0) -> float | None:
    """Annualised root-mean-square of returns below `target`."""
    if len(returns) < 2:
        return None
    shortfalls = [min(r - target, 0.0) ** 2 for r in returns]
    return math.sqrt(sum(shortfalls) / len(returns)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def drawdown_series(values: list[float]) -> list[float]:
    """Fractional fall from the running peak at each point (0 at a new high)."""
    out: list[float] = []
    peak = -math.inf
    for v in values:
        peak = max(peak, v)
        out.append(v / peak - 1.0 if peak > 0 else 0.0)
    return out


def historical_var(returns: list[float], confidence: float = 0.95) -> float | None:
    """
    One-day historical value at risk: the return at the (1 - confidence) quantile.

    Empirical rather than parametric, so it reflects the fat tails actually present
    in the series instead of assuming them away. Needs enough observations for the
    quantile to be more than a single data point.
    """
    if len(returns) < 20:
        return None
    ordered = sorted(returns)
    # Linear interpolation between the bracketing order statistics.
    position = (1.0 - confidence) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def beta_and_correlation(
    returns: list[float], benchmark_returns: list[float]
) -> tuple[float | None, float | None]:
    """Beta to, and correlation with, the benchmark over paired daily returns."""
    n = min(len(returns), len(benchmark_returns))
    if n < 2:
        return None, None
    xs, ys = benchmark_returns[:n], returns[:n]
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    var_x = sum((x - mx) ** 2 for x in xs) / (n - 1)
    var_y = sum((y - my) ** 2 for y in ys) / (n - 1)
    beta = cov / var_x if var_x > 0 else None
    corr = cov / math.sqrt(var_x * var_y) if var_x > 0 and var_y > 0 else None
    return beta, corr


def tracking_error(returns: list[float], benchmark_returns: list[float]) -> float | None:
    """Annualised standard deviation of daily active returns."""
    n = min(len(returns), len(benchmark_returns))
    active = [returns[i] - benchmark_returns[i] for i in range(n)]
    std = _sample_std(active)
    return None if std is None else std * math.sqrt(TRADING_DAYS_PER_YEAR)


def monthly_returns(points: list[Point]) -> list[dict[str, float | int]]:
    """
    Calendar-month returns, each measured from the previous month's last value.

    The first month is measured from the first point in the series, so a series
    that begins mid-month reports a partial first month rather than omitting it.
    """
    if len(points) < 2:
        return []

    out: list[dict[str, float | int]] = []
    anchor = points[0].value
    current = (points[0].day.year, points[0].day.month)
    last_value = points[0].value

    for p in points[1:]:
        key = (p.day.year, p.day.month)
        if key != current:
            if anchor > 0:
                out.append(
                    {"year": current[0], "month": current[1], "return": last_value / anchor - 1.0}
                )
            anchor = last_value
            current = key
        last_value = p.value

    if anchor > 0:
        out.append({"year": current[0], "month": current[1], "return": last_value / anchor - 1.0})
    return out


def trailing_return(points: list[Point], start: date) -> float | None:
    """
    Return from the last value on or before `start` to the latest value.

    None if the series does not reach back to `start`: reporting a "1 year" return
    computed over seven months of data would be a mislabelled number.
    """
    if not points or points[0].day > start:
        return None
    base = None
    for p in points:
        if p.day <= start:
            base = p.value
        else:
            break
    if base is None or base <= 0:
        return None
    return points[-1].value / base - 1.0


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(denominator) < 1e-12:
        return None
    return numerator / denominator


def summarize(
    points: list[Point],
    benchmark: list[Point] | None = None,
    risk_free_rate: float = 0.0,
) -> dict[str, float | None]:
    """
    Headline statistics for a level series, optionally against a benchmark.

    `benchmark` must be aligned to `points` (same dates, same length); alignment is
    the caller's job because only the caller knows how gaps should be filled.
    """
    values = [p.value for p in points]
    returns = daily_returns(values)
    drawdowns = drawdown_series(values)

    ann_return = annualized_return(points)
    vol = annualized_volatility(returns)
    downside = downside_deviation(returns)
    max_dd = min(drawdowns) if drawdowns else None
    excess = None if ann_return is None else ann_return - risk_free_rate

    stats: dict[str, float | None] = {
        "total_return": total_return(values),
        "annualized_return": ann_return,
        "volatility": vol,
        "sharpe_ratio": _ratio(excess, vol),
        "sortino_ratio": _ratio(excess, downside),
        "max_drawdown": max_dd,
        "current_drawdown": drawdowns[-1] if drawdowns else None,
        "calmar_ratio": _ratio(ann_return, abs(max_dd) if max_dd else None),
        "var_95": historical_var(returns, 0.95),
        "var_99": historical_var(returns, 0.99),
        "best_day": max(returns) if returns else None,
        "worst_day": min(returns) if returns else None,
        "positive_days": (sum(1 for r in returns if r > 0) / len(returns)) if returns else None,
        "benchmark_total_return": None,
        "benchmark_annualized_return": None,
        "benchmark_volatility": None,
        "excess_return": None,
        "beta": None,
        "correlation": None,
        "tracking_error": None,
        "information_ratio": None,
    }

    if benchmark and len(benchmark) == len(points):
        bench_values = [p.value for p in benchmark]
        bench_returns = daily_returns(bench_values)
        bench_total = total_return(bench_values)
        bench_ann = annualized_return(benchmark)
        beta, corr = beta_and_correlation(returns, bench_returns)
        te = tracking_error(returns, bench_returns)
        active_ann = None if ann_return is None or bench_ann is None else ann_return - bench_ann

        stats.update(
            benchmark_total_return=bench_total,
            benchmark_annualized_return=bench_ann,
            benchmark_volatility=annualized_volatility(bench_returns),
            excess_return=(
                None
                if stats["total_return"] is None or bench_total is None
                else stats["total_return"] - bench_total
            ),
            beta=beta,
            correlation=corr,
            tracking_error=te,
            information_ratio=_ratio(active_ann, te),
        )

    return stats
