"""Timezone, shift detection, and period helper utilities.

Provides functions for working with the CFT's operational schedule,
detecting current shifts, and computing time-based aggregation periods.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


# Shift boundaries (24h format, Portuguese factory schedule)
SHIFT_MORNING = (6, 14)  # 06:00 - 14:00
SHIFT_AFTERNOON = (14, 22)  # 14:00 - 22:00
LUNCH_BREAK = (12, 13)  # 12:00 - 13:00


def current_shift(dt: datetime | None = None) -> str:
    """Determine the active shift for a given datetime.

    Args:
        dt: Datetime to evaluate. Defaults to now.

    Returns:
        Shift name: 'morning', 'afternoon', 'night', or 'off_hours'.
    """
    if dt is None:
        dt = datetime.now()
    if is_weekend(dt):
        return "off_hours"
    return detect_shift(dt.hour)


def detect_shift(hour: int) -> str:
    """Detect which shift a given hour falls into.

    Args:
        hour: Hour of day (0-23).

    Returns:
        Shift name: 'morning', 'afternoon', or 'night'.
    """
    if SHIFT_MORNING[0] <= hour < SHIFT_MORNING[1]:
        return "morning"
    if SHIFT_AFTERNOON[0] <= hour < SHIFT_AFTERNOON[1]:
        return "afternoon"
    return "night"


def is_weekend(dt: datetime | None = None) -> bool:
    """Check if a datetime falls on a weekend.

    Args:
        dt: Datetime to check. Defaults to now.

    Returns:
        True if Saturday or Sunday.
    """
    if dt is None:
        dt = datetime.now()
    return dt.weekday() >= 5


def is_business_hours(dt: datetime | None = None) -> bool:
    """Check if a datetime falls within business hours.

    Business hours: weekdays 06:00-22:00.

    Args:
        dt: Datetime to check. Defaults to now.

    Returns:
        True if within business hours.
    """
    if dt is None:
        dt = datetime.now()
    if is_weekend(dt):
        return False
    return SHIFT_MORNING[0] <= dt.hour < SHIFT_AFTERNOON[1]


def get_period_range(
    period: str,
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Get start and end datetimes for a named period.

    Args:
        period: Period name ('today', 'yesterday', 'this_week',
                'this_month', 'last_7d', 'last_30d').
        reference: Reference datetime. Defaults to now.

    Returns:
        Tuple of (start, end) datetimes.
    """
    if reference is None:
        reference = datetime.now()

    today_start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1) - timedelta(microseconds=1)

    if period == "today":
        return today_start, today_end

    if period == "yesterday":
        yday_start = today_start - timedelta(days=1)
        return yday_start, today_start - timedelta(microseconds=1)

    if period == "this_week":
        # Monday = start of week
        week_start = today_start - timedelta(days=reference.weekday())
        return week_start, today_end

    if period == "this_month":
        month_start = today_start.replace(day=1)
        return month_start, today_end

    if period == "last_7d":
        return today_start - timedelta(days=7), today_end

    if period == "last_30d":
        return today_start - timedelta(days=30), today_end

    # Default: last 24 hours
    return reference - timedelta(hours=24), reference


def is_holiday(d: date | None = None) -> bool:
    """Check if a date is a Portuguese public holiday.

    Args:
        d: Date to check. Defaults to today.

    Returns:
        True if the date is a holiday.
    """
    if d is None:
        d = date.today()

    from data.synthetic.events import generate_holidays

    holidays = generate_holidays(d.year)
    return d in holidays
