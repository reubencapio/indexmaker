"""When scheduled work is due."""

from datetime import datetime, timezone

import pytest

from app.services.schedule import is_due, latest_market_close, latest_slot


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class TestLatestSlot:
    def test_daily_slot_is_today_once_the_time_has_passed(self):
        assert latest_slot("daily", "08:00", None, utc(2026, 10, 14, 9, 30)) == utc(2026, 10, 14, 8)

    def test_daily_slot_is_yesterday_before_the_time(self):
        assert latest_slot("daily", "08:00", None, utc(2026, 10, 14, 7, 59)) == utc(2026, 10, 13, 8)

    def test_weekly_slot_falls_on_the_chosen_weekday(self):
        # 14 October 2026 is a Wednesday; the schedule is Monday (0).
        assert latest_slot("weekly", "08:00", 0, utc(2026, 10, 14, 12)) == utc(2026, 10, 12, 8)

    def test_weekly_slot_on_the_day_but_before_the_time_is_last_week(self):
        assert latest_slot("weekly", "08:00", 2, utc(2026, 10, 14, 7)) == utc(2026, 10, 7, 8)

    def test_monthly_slot_before_the_day_is_last_month(self):
        assert latest_slot("monthly", "08:00", 15, utc(2026, 10, 14, 12)) == utc(2026, 9, 15, 8)

    def test_monthly_day_31_means_the_last_day_of_a_short_month(self):
        assert latest_slot("monthly", "08:00", 31, utc(2026, 3, 5, 12)) == utc(2026, 2, 28, 8)

    def test_monthly_slot_wraps_the_year(self):
        assert latest_slot("monthly", "08:00", 20, utc(2026, 1, 3, 12)) == utc(2025, 12, 20, 8)

    @pytest.mark.parametrize("bad", [None, "", "nonsense", "25:99"])
    def test_missing_or_bad_time_defaults_to_eight(self, bad):
        assert latest_slot("daily", bad, None, utc(2026, 10, 14, 12)).hour == 8


class TestIsDue:
    def test_due_when_a_slot_has_passed_since_the_last_send(self):
        assert is_due(
            "daily", "08:00", None, utc(2026, 10, 13, 8, 1), None, utc(2026, 10, 14, 8, 20)
        )

    def test_not_due_twice_for_the_same_slot(self):
        sent = utc(2026, 10, 14, 8, 20)
        assert not is_due("daily", "08:00", None, sent, None, utc(2026, 10, 14, 9, 20))

    def test_a_missed_tick_is_caught_up_later(self):
        # The 08:00 tick never ran; the report still goes at the next opportunity.
        assert is_due("daily", "08:00", None, utc(2026, 10, 13, 8, 5), None, utc(2026, 10, 14, 15))

    def test_a_new_schedule_waits_for_its_first_slot(self):
        created = utc(2026, 10, 14, 10)
        assert not is_due("weekly", "08:00", 0, None, created, utc(2026, 10, 14, 11))
        assert is_due("weekly", "08:00", 0, None, created, utc(2026, 10, 19, 8, 20))

    def test_naive_timestamps_are_read_as_utc(self):
        assert is_due(
            "daily", "08:00", None, datetime(2026, 10, 13, 8, 1), None, utc(2026, 10, 14, 9)
        )


class TestLatestMarketClose:
    def test_weekday_evening_is_that_day(self):
        assert latest_market_close(utc(2026, 10, 14, 22)) == utc(2026, 10, 14, 21, 30)

    def test_weekday_morning_is_the_previous_day(self):
        assert latest_market_close(utc(2026, 10, 14, 9)) == utc(2026, 10, 13, 21, 30)

    def test_weekend_and_monday_morning_point_at_friday(self):
        friday = utc(2026, 10, 9, 21, 30)
        assert latest_market_close(utc(2026, 10, 10, 12)) == friday
        assert latest_market_close(utc(2026, 10, 11, 23)) == friday
        assert latest_market_close(utc(2026, 10, 12, 9)) == friday
