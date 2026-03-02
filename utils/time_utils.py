"""Timezone, shift detection, and period helper utilities.

Provides functions for working with the CFT's operational schedule,
detecting current shifts, and computing time-based aggregation periods.
"""

from __future__ import annotations

from datetime import date, datetime


# Shift boundaries (24h format, Portuguese factory schedule)
SHIFT_MORNING = (6, 14)   # 06:00 - 14:00
SHIFT_AFTERNOON = (14, 22)  # 14:00 - 22:00
LUNCH_BREAK = (12, 13)  # 12:00 - 13:00


def current_shift(dt: datetime | None = None) -> str:
    """Determine the active shift for a given datetime.

    Args:
        dt: Datetime to evaluate. Defaults to now.

    Returns:
        Shift name: 'morning', 'afternoon', 'night', or 'off_hours'.
    """
    ...


def detect_shift(hour: int) -> str:
    """Detect which shift a given hour falls into.

    Args:
        hour: Hour of day (0-23).

    Returns:
        Shift name: 'morning', 'afternoon', or 'night'.
    """
    ...


def is_weekend(dt: datetime | None = None) -> bool:
    """Check if a datetime falls on a weekend.

    Args:
        dt: Datetime to check. Defaults to now.

    Returns:
        True if Saturday or Sunday.
    """
    ...


def is_business_hours(dt: datetime | None = None) -> bool:
    """Check if a datetime falls within business hours.

    Business hours: weekdays 06:00-22:00.

    Args:
        dt: Datetime to check. Defaults to now.

    Returns:
        True if within business hours.
    """
    ...


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
    ...


def is_holiday(d: date | None = None) -> bool:
    """Check if a date is a Portuguese public holiday.

    Args:
        d: Date to check. Defaults to today.

    Returns:
        True if the date is a holiday.
    """
    ...
