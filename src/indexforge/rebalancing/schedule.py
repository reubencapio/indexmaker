"""
Rebalancing schedule for index maintenance.

Defines when and how index rebalancing occurs.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from indexforge.core.types import RebalancingFrequency


@dataclass
class RebalancingSchedule:
    """
    Defines the rebalancing schedule for an index.

    Specifies when constituents are reviewed and weights are adjusted.

    Attributes:
        frequency: How often to rebalance
        months: Specific months for rebalancing (1-12)
        day: Day of month for rebalancing
        selection_date_offset: Business days before rebalance for selection
        announcement_date_offset: Business days before rebalance for announcement

    Example:
        >>> schedule = RebalancingSchedule.quarterly()
        >>> schedule = (RebalancingSchedule.builder()
        ...     .frequency("quarterly")
        ...     .on_months([3, 6, 9, 12])
        ...     .on_day(15)
        ...     .build()
        ... )
    """

    frequency: RebalancingFrequency = RebalancingFrequency.QUARTERLY
    months: list[int] = field(default_factory=lambda: [3, 6, 9, 12])
    day: int = 15
    selection_date_offset: int = 5  # Business days before rebalance
    announcement_date_offset: int = 2  # Business days before rebalance

    @staticmethod
    def builder() -> "RebalancingScheduleBuilder":
        """Create a new RebalancingScheduleBuilder."""
        return RebalancingScheduleBuilder()

    @staticmethod
    def quarterly() -> "RebalancingSchedule":
        """
        Create quarterly rebalancing schedule.

        Rebalances in March, June, September, and December.

        Returns:
            RebalancingSchedule for quarterly rebalancing
        """
        return RebalancingSchedule(
            frequency=RebalancingFrequency.QUARTERLY,
            months=[3, 6, 9, 12],
            day=15,
        )

    @staticmethod
    def monthly(day: int = 1) -> "RebalancingSchedule":
        """
        Create monthly rebalancing schedule.

        Args:
            day: Day of month for rebalancing

        Returns:
            RebalancingSchedule for monthly rebalancing
        """
        return RebalancingSchedule(
            frequency=RebalancingFrequency.MONTHLY,
            months=list(range(1, 13)),
            day=day,
        )

    @staticmethod
    def semi_annual(months: Optional[list[int]] = None, day: int = 15) -> "RebalancingSchedule":
        """
        Create semi-annual rebalancing schedule.

        Args:
            months: Months for rebalancing (default: June and December)
            day: Day of month for rebalancing

        Returns:
            RebalancingSchedule for semi-annual rebalancing
        """
        return RebalancingSchedule(
            frequency=RebalancingFrequency.SEMI_ANNUAL,
            months=months or [6, 12],
            day=day,
        )

    @staticmethod
    def annual(month: int = 12, day: int = 15) -> "RebalancingSchedule":
        """
        Create annual rebalancing schedule.

        Args:
            month: Month for rebalancing
            day: Day of month for rebalancing

        Returns:
            RebalancingSchedule for annual rebalancing
        """
        return RebalancingSchedule(
            frequency=RebalancingFrequency.ANNUAL,
            months=[month],
            day=day,
        )

    def get_rebalancing_dates(self, start_date: date, end_date: date) -> list[date]:
        """
        Get all rebalancing dates within a period.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            List of rebalancing dates
        """
        dates = []
        current_year = start_date.year

        while current_year <= end_date.year:
            for month in self.months:
                try:
                    rebal_date = date(current_year, month, self.day)
                    if start_date <= rebal_date <= end_date:
                        # Adjust for weekends
                        rebal_date = self._adjust_for_weekend(rebal_date)
                        dates.append(rebal_date)
                except ValueError:
                    # Invalid date (e.g., Feb 30), use last day of month
                    if month == 2:
                        rebal_date = date(current_year, month, 28)
                    else:
                        rebal_date = date(current_year, month, 30)
                    if start_date <= rebal_date <= end_date:
                        rebal_date = self._adjust_for_weekend(rebal_date)
                        dates.append(rebal_date)
            current_year += 1

        return sorted(dates)

    def get_selection_date(self, rebalancing_date: date) -> date:
        """
        Get the selection (data) date for a rebalancing.

        Args:
            rebalancing_date: The rebalancing effective date

        Returns:
            The date when selection data should be taken
        """
        return self._subtract_business_days(rebalancing_date, self.selection_date_offset)

    def get_announcement_date(self, rebalancing_date: date) -> date:
        """
        Get the announcement date for a rebalancing.

        Args:
            rebalancing_date: The rebalancing effective date

        Returns:
            The date when changes should be announced
        """
        return self._subtract_business_days(rebalancing_date, self.announcement_date_offset)

    def is_rebalancing_date(self, check_date: date) -> bool:
        """
        Check if a date is a rebalancing date.

        Args:
            check_date: Date to check

        Returns:
            True if the date is a rebalancing date
        """
        if check_date.month not in self.months:
            return False

        if check_date.day != self.day:
            # Check if it's weekend-adjusted
            expected = date(check_date.year, check_date.month, self.day)
            adjusted = self._adjust_for_weekend(expected)
            return check_date == adjusted

        return True

    def get_next_rebalancing_date(self, from_date: date) -> Optional[date]:
        """
        Get the next rebalancing date from a given date.

        Args:
            from_date: Starting date

        Returns:
            Next rebalancing date, or None if not found within 2 years
        """
        end_date = date(from_date.year + 2, from_date.month, from_date.day)
        dates = self.get_rebalancing_dates(from_date + timedelta(days=1), end_date)
        return dates[0] if dates else None

    def _adjust_for_weekend(self, d: date) -> date:
        """Adjust date if it falls on a weekend."""
        if d.weekday() == 5:  # Saturday
            return d - timedelta(days=1)
        elif d.weekday() == 6:  # Sunday
            return d + timedelta(days=1)
        return d

    def _subtract_business_days(self, d: date, days: int) -> date:
        """Subtract business days from a date."""
        result = d
        days_subtracted = 0
        while days_subtracted < days:
            result -= timedelta(days=1)
            if result.weekday() < 5:  # Monday = 0, Friday = 4
                days_subtracted += 1
        return result

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "frequency": str(self.frequency),
            "months": self.months,
            "day": self.day,
            "selection_date_offset": self.selection_date_offset,
            "announcement_date_offset": self.announcement_date_offset,
        }


class RebalancingScheduleBuilder:
    """
    Builder for constructing RebalancingSchedule with fluent syntax.

    Example:
        >>> schedule = (RebalancingSchedule.builder()
        ...     .frequency("quarterly")
        ...     .on_months([3, 6, 9, 12])
        ...     .on_day(15)
        ...     .selection_date_offset(5)
        ...     .announcement_date_offset(2)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        self._frequency: RebalancingFrequency = RebalancingFrequency.QUARTERLY
        self._months: list[int] = [3, 6, 9, 12]
        self._day: int = 15
        self._selection_date_offset: int = 5
        self._announcement_date_offset: int = 2

    def frequency(self, freq: str) -> "RebalancingScheduleBuilder":
        """
        Set the rebalancing frequency.

        Args:
            freq: Frequency string (daily, weekly, monthly, quarterly, semi_annual, annual)
        """
        freq_upper = freq.upper().replace("-", "_").replace(" ", "_")
        self._frequency = RebalancingFrequency(freq_upper)

        # Set default months based on frequency
        if self._frequency == RebalancingFrequency.MONTHLY:
            self._months = list(range(1, 13))
        elif self._frequency == RebalancingFrequency.QUARTERLY:
            self._months = [3, 6, 9, 12]
        elif self._frequency == RebalancingFrequency.SEMI_ANNUAL:
            self._months = [6, 12]
        elif self._frequency == RebalancingFrequency.ANNUAL:
            self._months = [12]

        return self

    def on_months(self, months: list[int]) -> "RebalancingScheduleBuilder":
        """
        Set specific months for rebalancing.

        Args:
            months: List of months (1-12)
        """
        for m in months:
            if not 1 <= m <= 12:
                raise ValueError(f"Month must be between 1 and 12, got {m}")
        self._months = months
        return self

    def on_day(self, day: int) -> "RebalancingScheduleBuilder":
        """
        Set the day of month for rebalancing.

        Args:
            day: Day of month (1-31)
        """
        if not 1 <= day <= 31:
            raise ValueError(f"Day must be between 1 and 31, got {day}")
        self._day = day
        return self

    def selection_date_offset(self, days: int) -> "RebalancingScheduleBuilder":
        """
        Set business days offset for selection date.

        Args:
            days: Number of business days before rebalancing
        """
        if days < 0:
            raise ValueError("Offset must be non-negative")
        self._selection_date_offset = days
        return self

    def announcement_date_offset(self, days: int) -> "RebalancingScheduleBuilder":
        """
        Set business days offset for announcement date.

        Args:
            days: Number of business days before rebalancing
        """
        if days < 0:
            raise ValueError("Offset must be non-negative")
        self._announcement_date_offset = days
        return self

    def build(self) -> RebalancingSchedule:
        """Build the RebalancingSchedule object."""
        return RebalancingSchedule(
            frequency=self._frequency,
            months=self._months,
            day=self._day,
            selection_date_offset=self._selection_date_offset,
            announcement_date_offset=self._announcement_date_offset,
        )
