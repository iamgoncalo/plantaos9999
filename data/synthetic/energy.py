"""Synthetic energy consumption profiles.

Generates realistic kWh data for HVAC (60%), lighting (20%),
equipment (15%), and other (5%) with time-of-day, day-of-week,
and seasonal patterns. March in Aveiro climate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_energy_data(
    zones: list[dict],
    days: int = 30,
    interval_min: int = 15,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate energy consumption data for all zones.

    Args:
        zones: List of zone dicts with 'id', 'area_m2', 'has_hvac' keys.
        days: Number of days of history.
        interval_min: Time resolution in minutes.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, zone_id, hvac_kwh,
        lighting_kwh, equipment_kwh, other_kwh, total_kwh.
    """
    ...


def _hvac_load_factor(hour: int, day_of_week: int, month: int) -> float:
    """Calculate HVAC load factor based on temporal patterns.

    Args:
        hour: Hour of day (0-23).
        day_of_week: Day of week (0=Monday, 6=Sunday).
        month: Month (1-12).

    Returns:
        Load factor between 0.0 and 1.0.
    """
    ...


def _lighting_load_factor(hour: int, day_of_week: int) -> float:
    """Calculate lighting load factor.

    Args:
        hour: Hour of day (0-23).
        day_of_week: Day of week.

    Returns:
        Load factor between 0.0 and 1.0.
    """
    ...


def _equipment_load_factor(hour: int, day_of_week: int) -> float:
    """Calculate equipment load factor.

    Args:
        hour: Hour of day (0-23).
        day_of_week: Day of week.

    Returns:
        Load factor between 0.0 and 1.0.
    """
    ...
