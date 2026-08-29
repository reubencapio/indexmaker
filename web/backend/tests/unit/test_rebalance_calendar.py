"""
Unit tests for rebalance date selection.

A backtest that never rebalances is not testing the methodology the user defined,
so these pin down which trading days trigger a reallocation.
"""

from datetime import date, timedelta

from app.services.rebalance_calendar import rebalance_dates


def _weekdays(start: date, count: int) -> list[date]:
    """A run of consecutive weekdays, standing in for a trading calendar."""
    days: list[date] = []
    day = start
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


class TestFrequencies:
    def test_daily_rebalances_every_day_but_inception(self):
        days = _weekdays(date(2026, 1, 5), 10)
        assert rebalance_dates(days, "daily") == set(days[1:])

    def test_weekly_picks_one_day_per_week(self):
        days = _weekdays(date(2026, 1, 5), 20)  # four full weeks
        result = rebalance_dates(days, "weekly")
        # First Monday is inception, so three remaining week-starts.
        assert len(result) == 3
        assert all(d.weekday() == 0 for d in result)

    def test_monthly_picks_first_trading_day_of_each_month(self):
        days = _weekdays(date(2026, 1, 1), 90)  # roughly 18 weeks, into May
        result = sorted(rebalance_dates(days, "monthly"))
        assert [d.month for d in result] == [2, 3, 4, 5]
        assert all(d.day <= 3 for d in result), "should land on each month's first trading day"

    def test_quarterly_picks_four_dates_a_year(self):
        days = _weekdays(date(2026, 1, 1), 260)
        result = sorted(rebalance_dates(days, "quarterly"))
        assert [d.month for d in result] == [4, 7, 10]

    def test_semi_annual_picks_the_july_boundary(self):
        days = _weekdays(date(2026, 1, 1), 260)
        result = sorted(rebalance_dates(days, "semi_annual"))
        assert [d.month for d in result] == [7]

    def test_annual_rebalances_at_each_year_boundary(self):
        days = _weekdays(date(2026, 1, 1), 400)
        result = sorted(rebalance_dates(days, "annual"))
        assert [d.year for d in result] == [2027]


class TestEdgeCases:
    def test_inception_is_never_a_rebalance_day(self):
        days = _weekdays(date(2026, 1, 1), 60)
        for frequency in ("daily", "weekly", "monthly", "quarterly", "annual"):
            assert days[0] not in rebalance_dates(days, frequency)

    def test_period_boundary_on_a_weekend_moves_to_the_next_trading_day(self):
        # 1 March 2026 is a Sunday; the first March trading day is the 2nd.
        days = _weekdays(date(2026, 2, 20), 15)
        result = rebalance_dates(days, "monthly")
        assert date(2026, 3, 2) in result

    def test_unknown_frequency_yields_no_rebalances(self):
        days = _weekdays(date(2026, 1, 1), 30)
        assert rebalance_dates(days, "fortnightly") == set()

    def test_single_day_has_no_rebalances(self):
        assert rebalance_dates([date(2026, 1, 5)], "daily") == set()

    def test_empty_calendar_has_no_rebalances(self):
        assert rebalance_dates([], "monthly") == set()
