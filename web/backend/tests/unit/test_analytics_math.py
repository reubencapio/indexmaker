"""
Tests for the analytics arithmetic.

Expected values are worked out by hand in the comments so a failure points at the
formula, not at another implementation of it.
"""

import math
from datetime import date, timedelta

import pytest

from app.services import analytics_math as am
from app.services.analytics_math import Point
from app.services.analytics_service import align, build_level_series, period_start


def series(values: list[float], start: date = date(2024, 1, 1)) -> list[Point]:
    return [Point(start + timedelta(days=i), v) for i, v in enumerate(values)]


def test_daily_and_total_return():
    assert am.daily_returns([100, 110, 99]) == pytest.approx([0.10, -0.10])
    assert am.total_return([100, 110, 99]) == pytest.approx(-0.01)
    assert am.total_return([100]) is None


def test_annualized_return_is_cagr_over_calendar_time():
    # Doubling over exactly two years is sqrt(2) - 1 a year, however many
    # observations there happen to be.
    points = [Point(date(2022, 1, 1), 100.0), Point(date(2024, 1, 1), 200.0)]
    assert am.annualized_return(points) == pytest.approx(math.sqrt(2) - 1, abs=1e-3)


def test_annualized_return_refuses_very_short_spans():
    assert am.annualized_return(series([100, 101, 102])) is None


def test_volatility_uses_sample_std_and_sqrt_252():
    returns = [0.01, -0.01, 0.01, -0.01]
    # mean 0, sample variance = 4 * 0.0001 / 3
    expected = math.sqrt(0.0004 / 3) * math.sqrt(252)
    assert am.annualized_volatility(returns) == pytest.approx(expected)
    assert am.annualized_volatility([0.01]) is None


def test_drawdown_series_and_max():
    dd = am.drawdown_series([100, 120, 90, 108, 130])
    assert dd == pytest.approx([0, 0, -0.25, -0.10, 0])


def test_historical_var_needs_enough_observations():
    assert am.historical_var([0.01] * 10) is None
    returns = [i / 1000 for i in range(-50, 51)]  # -5% .. +5%, 101 points
    # 5th percentile of an even grid from -0.05 to 0.05 is -0.045.
    assert am.historical_var(returns, 0.95) == pytest.approx(-0.045)


def test_beta_of_a_levered_copy_is_the_leverage():
    bench = [0.01, -0.02, 0.015, 0.005, -0.01]
    beta, corr = am.beta_and_correlation([2 * r for r in bench], bench)
    assert beta == pytest.approx(2.0)
    assert corr == pytest.approx(1.0)


def test_tracking_error_is_zero_against_itself():
    r = [0.01, -0.02, 0.015]
    assert am.tracking_error(r, r) == pytest.approx(0.0)


def test_monthly_returns_chain_from_previous_month_end():
    points = [
        Point(date(2024, 1, 30), 100.0),
        Point(date(2024, 1, 31), 110.0),
        Point(date(2024, 2, 15), 121.0),
        Point(date(2024, 2, 29), 99.0),
    ]
    months = am.monthly_returns(points)
    assert [(m["year"], m["month"]) for m in months] == [(2024, 1), (2024, 2)]
    assert months[0]["return"] == pytest.approx(0.10)
    # February is measured from January's close (110), not from its own first print.
    assert months[1]["return"] == pytest.approx(99 / 110 - 1)


def test_trailing_return_is_none_when_history_is_too_short():
    points = series([100, 105, 110], start=date(2024, 6, 1))
    assert am.trailing_return(points, date(2024, 1, 1)) is None
    assert am.trailing_return(points, date(2024, 6, 1)) == pytest.approx(0.10)


def test_summarize_reports_none_rather_than_zero_for_unknowns():
    stats = am.summarize(series([100, 101]))
    assert stats["total_return"] == pytest.approx(0.01)
    assert stats["sharpe_ratio"] is None
    assert stats["beta"] is None


def test_summarize_against_benchmark():
    idx = series([100 * 1.001**i for i in range(300)])
    bench = series([50 * 1.0005**i for i in range(300)])
    stats = am.summarize(idx, bench)
    assert stats["excess_return"] == pytest.approx(
        (1.001**299 - 1) - (1.0005**299 - 1), rel=1e-9
    )
    assert stats["max_drawdown"] == pytest.approx(0.0)


def test_level_series_values_fixed_shares_and_anchors_to_published_level():
    d1, d2, d3 = date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)
    prices = {"A": {d1: 10.0, d2: 11.0, d3: 12.0}, "B": {d1: 20.0, d2: 20.0, d3: 18.0}}
    points, excluded, limiting = build_level_series({"A": 1.0, "B": 2.0}, prices, 960.0)
    # Raw market value: 50, 51, 48. Rescaled so the last point is 960.
    assert [p.value for p in points] == pytest.approx([1000.0, 1020.0, 960.0])
    assert excluded == [] and limiting is None


def test_level_series_starts_when_every_holding_has_traded():
    d1, d2, d3 = date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)
    prices = {"OLD": {d1: 10.0, d2: 10.0, d3: 10.0}, "IPO": {d2: 5.0, d3: 6.0}, "DEAD": {}}
    points, excluded, limiting = build_level_series(
        {"OLD": 1.0, "IPO": 1.0, "DEAD": 1.0}, prices, None
    )
    assert [p.day for p in points] == [d2, d3]
    assert excluded == ["DEAD"]
    assert limiting == "IPO"


def test_level_series_forward_fills_gaps():
    d1, d2, d3 = date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)
    prices = {"A": {d1: 10.0, d3: 12.0}, "B": {d1: 1.0, d2: 1.0, d3: 1.0}}
    points, _, _ = build_level_series({"A": 1.0, "B": 1.0}, prices, None)
    assert [p.value for p in points] == pytest.approx([11.0, 11.0, 13.0])


def test_align_returns_none_if_benchmark_starts_late():
    points = series([1, 2, 3])
    assert align(points, {points[1].day: 5.0}) is None
    aligned = align(points, {points[0].day: 5.0, points[2].day: 6.0})
    assert [p.value for p in aligned] == [5.0, 5.0, 6.0]


def test_ytd_anchors_on_prior_year_end():
    assert period_start("YTD", date(2026, 10, 6)) == date(2025, 12, 31)
