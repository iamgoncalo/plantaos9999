"""Number, date, and unit formatting utilities.

Provides consistent formatting for display values across the dashboard,
including locale-aware numbers, energy units, and date/time strings.
"""

from __future__ import annotations

from datetime import datetime


def format_number(value: float, decimals: int = 1, suffix: str = "") -> str:
    """Format a number with thousand separators and optional suffix.

    Args:
        value: Numeric value to format.
        decimals: Number of decimal places.
        suffix: Unit suffix (e.g., 'kWh', '%').

    Returns:
        Formatted string like '1,234.5 kWh'.
    """
    ...


def format_energy(kwh: float) -> str:
    """Format energy value with appropriate unit (Wh, kWh, MWh).

    Args:
        kwh: Energy in kilowatt-hours.

    Returns:
        Formatted string with auto-scaled unit.
    """
    ...


def format_temperature(celsius: float) -> str:
    """Format temperature with degree symbol and unit.

    Args:
        celsius: Temperature in degrees Celsius.

    Returns:
        Formatted string like '22.5 °C'.
    """
    ...


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a percentage value.

    Args:
        value: Percentage value (0-100).
        decimals: Decimal places.

    Returns:
        Formatted string like '85.2%'.
    """
    ...


def format_date(dt: datetime, fmt: str = "short") -> str:
    """Format a datetime for display.

    Args:
        dt: Datetime object.
        fmt: Format style ('short', 'long', 'time', 'date').

    Returns:
        Formatted datetime string.
    """
    ...


def format_trend(current: float, previous: float) -> tuple[str, str]:
    """Calculate and format a trend indicator.

    Args:
        current: Current metric value.
        previous: Previous period metric value.

    Returns:
        Tuple of (trend_text, direction) e.g., ('+5.2%', 'up').
    """
    ...
