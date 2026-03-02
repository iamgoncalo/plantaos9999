"""Synthetic event generation for weather, schedules, and holidays.

Generates external events that influence building behavior:
weather conditions for March in Aveiro, shift schedule changes,
and Portuguese public holiday markers.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def generate_weather(
    days: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic weather data for Aveiro in March.

    March in Aveiro: 8-18°C, occasional rain, humidity 60-85%.

    Args:
        days: Number of days.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, outdoor_temp_c,
        outdoor_humidity_pct, solar_radiation_w_m2, wind_speed_ms,
        is_raining.
    """
    ...


def generate_shift_schedule(
    days: int = 30,
) -> pd.DataFrame:
    """Generate shift schedule markers.

    Portuguese factory shifts: 6h-14h morning, 14h-22h afternoon.

    Args:
        days: Number of days.

    Returns:
        DataFrame with columns: timestamp, shift, is_business_hours,
        is_weekend.
    """
    ...


def generate_holidays(year: int = 2026) -> list[date]:
    """Return Portuguese public holidays for a given year.

    Args:
        year: Calendar year.

    Returns:
        List of holiday dates.
    """
    ...
