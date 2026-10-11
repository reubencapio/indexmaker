"""
When scheduled work is due.

Everything here is a pure function of the clock. Jobs are driven by "is this
overdue?" rather than "is it exactly 08:00?": the scheduler ticks hourly, but a
tick can be missed (a deploy, a restart, a sleeping instance), and a report that
is skipped for good because the process was down at the appointed minute is
worse than one that arrives an hour late.
"""

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta, timezone

DEFAULT_SEND_TIME = time(8, 0)

# US cash close is 20:00 or 21:00 UTC depending on daylight saving; 21:30 is
# after both, with room for the data provider to publish closing prices.
MARKET_CLOSE_UTC = time(21, 30)


def _parse_time(value: str | None) -> time:
    if value:
        try:
            hour, minute = value.split(":")
            return time(int(hour), int(minute))
        except ValueError:
            pass
    return DEFAULT_SEND_TIME


def _at(day: datetime, at: time) -> datetime:
    return day.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)


def latest_slot(
    frequency: str, schedule_time: str | None, schedule_day: int | None, now: datetime
) -> datetime:
    """
    The most recent moment, at or before `now`, a schedule called for a send.

    `schedule_day` is the weekday for weekly schedules (0 = Monday) and the day
    of the month for monthly ones. Any other frequency is treated as daily.
    """
    now = now.astimezone(timezone.utc)
    at = _parse_time(schedule_time)

    if frequency == "weekly":
        weekday = schedule_day if schedule_day is not None and 0 <= schedule_day <= 6 else 0
        slot = _at(now - timedelta(days=(now.weekday() - weekday) % 7), at)
        return slot if slot <= now else slot - timedelta(days=7)

    if frequency == "monthly":
        wanted = schedule_day if schedule_day and 1 <= schedule_day <= 31 else 1

        def slot_in(year: int, month: int) -> datetime:
            # The 31st means "the last day" in a shorter month.
            day = min(wanted, calendar.monthrange(year, month)[1])
            return _at(now.replace(year=year, month=month, day=day), at)

        slot = slot_in(now.year, now.month)
        if slot <= now:
            return slot
        year, month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        return slot_in(year, month)

    slot = _at(now, at)
    return slot if slot <= now else slot - timedelta(days=1)


def is_due(
    frequency: str,
    schedule_time: str | None,
    schedule_day: int | None,
    last_sent_at: datetime | None,
    created_at: datetime | None,
    now: datetime,
) -> bool:
    """
    True if a send was scheduled since the last one went out.

    A new schedule counts from when it was created, so it waits for its first
    slot instead of firing on the next tick for a slot that predates it.
    """
    since = last_sent_at or created_at
    if since is None:
        return True
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return since < latest_slot(frequency, schedule_time, schedule_day, now)


def latest_market_close(now: datetime) -> datetime:
    """The most recent weekday close at or before `now`."""
    now = now.astimezone(timezone.utc)
    slot = _at(now, MARKET_CLOSE_UTC)
    if slot > now:
        slot -= timedelta(days=1)
    while slot.weekday() >= 5:
        slot -= timedelta(days=1)
    return slot
