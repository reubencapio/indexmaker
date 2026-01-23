"""Tests for rebalancing schedule."""

from datetime import date

import pytest

from indexforge.core.types import RebalancingFrequency
from indexforge.rebalancing.schedule import RebalancingSchedule


class TestRebalancingSchedule:
    """Tests for RebalancingSchedule class."""

    def test_quarterly_schedule(self):
        """Test quarterly rebalancing schedule."""
        schedule = RebalancingSchedule.quarterly()

        assert schedule.frequency == RebalancingFrequency.QUARTERLY
        assert schedule.months == [3, 6, 9, 12]
        assert schedule.day == 15

    def test_monthly_schedule(self):
        """Test monthly rebalancing schedule."""
        schedule = RebalancingSchedule.monthly(day=1)

        assert schedule.frequency == RebalancingFrequency.MONTHLY
        assert schedule.months == list(range(1, 13))
        assert schedule.day == 1

    def test_semi_annual_schedule(self):
        """Test semi-annual rebalancing schedule."""
        schedule = RebalancingSchedule.semi_annual()

        assert schedule.frequency == RebalancingFrequency.SEMI_ANNUAL
        assert schedule.months == [6, 12]

    def test_annual_schedule(self):
        """Test annual rebalancing schedule."""
        schedule = RebalancingSchedule.annual(month=12, day=31)

        assert schedule.frequency == RebalancingFrequency.ANNUAL
        assert schedule.months == [12]
        assert schedule.day == 31

    def test_get_rebalancing_dates(self):
        """Test getting rebalancing dates within a period."""
        schedule = RebalancingSchedule.quarterly()

        dates = schedule.get_rebalancing_dates(date(2024, 1, 1), date(2024, 12, 31))

        assert len(dates) == 4  # Q1, Q2, Q3, Q4

        # Check months
        months = [d.month for d in dates]
        assert months == [3, 6, 9, 12]

    def test_get_rebalancing_dates_partial_year(self):
        """Test getting rebalancing dates for partial year."""
        schedule = RebalancingSchedule.quarterly()

        dates = schedule.get_rebalancing_dates(date(2024, 4, 1), date(2024, 10, 1))

        assert len(dates) == 2  # Q2 and Q3
        months = [d.month for d in dates]
        assert months == [6, 9]

    def test_is_rebalancing_date(self):
        """Test checking if a date is a rebalancing date."""
        schedule = RebalancingSchedule.quarterly()  # 15th of Mar, Jun, Sep, Dec

        assert schedule.is_rebalancing_date(date(2024, 3, 15))
        assert schedule.is_rebalancing_date(date(2024, 6, 15))
        assert not schedule.is_rebalancing_date(date(2024, 4, 15))
        assert not schedule.is_rebalancing_date(date(2024, 3, 16))

    def test_get_next_rebalancing_date(self):
        """Test getting next rebalancing date."""
        schedule = RebalancingSchedule.quarterly()

        next_date = schedule.get_next_rebalancing_date(date(2024, 1, 1))

        assert next_date == date(2024, 3, 15)

    def test_get_selection_date(self):
        """Test getting selection date (before rebalancing)."""
        schedule = RebalancingSchedule(
            frequency=RebalancingFrequency.QUARTERLY,
            months=[3, 6, 9, 12],
            day=15,
            selection_date_offset=5,
        )

        rebal_date = date(2024, 3, 15)  # Friday
        selection_date = schedule.get_selection_date(rebal_date)

        # 5 business days before March 15, 2024 (Friday)
        # Should be March 8, 2024 (Friday)
        assert selection_date < rebal_date
        assert (rebal_date - selection_date).days >= 5

    def test_get_announcement_date(self):
        """Test getting announcement date."""
        schedule = RebalancingSchedule(
            frequency=RebalancingFrequency.QUARTERLY,
            months=[3, 6, 9, 12],
            day=15,
            announcement_date_offset=2,
        )

        rebal_date = date(2024, 3, 15)
        announcement_date = schedule.get_announcement_date(rebal_date)

        assert announcement_date < rebal_date

    def test_weekend_adjustment(self):
        """Test that dates are adjusted for weekends."""
        schedule = RebalancingSchedule(
            frequency=RebalancingFrequency.MONTHLY, months=[3], day=16  # March 16, 2024 is Saturday
        )

        dates = schedule.get_rebalancing_dates(date(2024, 3, 1), date(2024, 3, 31))

        assert len(dates) == 1
        # Should be adjusted (not Saturday or Sunday)
        assert dates[0].weekday() < 5

    def test_to_dict(self):
        """Test converting to dictionary."""
        schedule = RebalancingSchedule.quarterly()

        data = schedule.to_dict()

        assert data["frequency"] == "QUARTERLY"
        assert data["months"] == [3, 6, 9, 12]
        assert data["day"] == 15


class TestRebalancingScheduleBuilder:
    """Tests for RebalancingScheduleBuilder class."""

    def test_builder_basic(self):
        """Test basic builder usage."""
        schedule = (
            RebalancingSchedule.builder()
            .frequency("quarterly")
            .on_months([3, 6, 9, 12])
            .on_day(20)
            .build()
        )

        assert schedule.frequency == RebalancingFrequency.QUARTERLY
        assert schedule.months == [3, 6, 9, 12]
        assert schedule.day == 20

    def test_builder_with_offsets(self):
        """Test builder with date offsets."""
        schedule = (
            RebalancingSchedule.builder()
            .frequency("quarterly")
            .selection_date_offset(10)
            .announcement_date_offset(5)
            .build()
        )

        assert schedule.selection_date_offset == 10
        assert schedule.announcement_date_offset == 5

    def test_builder_sets_default_months(self):
        """Test that builder sets default months based on frequency."""
        quarterly = RebalancingSchedule.builder().frequency("quarterly").build()
        assert quarterly.months == [3, 6, 9, 12]

        monthly = RebalancingSchedule.builder().frequency("monthly").build()
        assert monthly.months == list(range(1, 13))

        annual = RebalancingSchedule.builder().frequency("annual").build()
        assert annual.months == [12]

    def test_invalid_month(self):
        """Test that invalid month raises error."""
        with pytest.raises(ValueError):
            RebalancingSchedule.builder().on_months([0]).build()

        with pytest.raises(ValueError):
            RebalancingSchedule.builder().on_months([13]).build()

    def test_invalid_day(self):
        """Test that invalid day raises error."""
        with pytest.raises(ValueError):
            RebalancingSchedule.builder().on_day(0).build()

        with pytest.raises(ValueError):
            RebalancingSchedule.builder().on_day(32).build()

    def test_invalid_offset(self):
        """Test that negative offset raises error."""
        with pytest.raises(ValueError):
            RebalancingSchedule.builder().selection_date_offset(-1).build()
