"""Synthetic occupancy and presence patterns.

Generates realistic occupancy data following Portuguese factory shifts
(6h-14h / 14h-22h), meeting patterns, lunch breaks (12h-13h),
and weekend minimal occupancy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_occupancy_data(
    zones: list[dict],
    days: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate occupancy data for all zones.

    Args:
        zones: List of zone dicts with 'id', 'capacity', 'zone_type' keys.
        days: Number of days of history.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, zone_id, occupant_count,
        occupancy_ratio, is_occupied.
    """
    ...


def _shift_occupancy_pattern(
    hour: int,
    day_of_week: int,
    zone_type: str,
) -> float:
    """Model occupancy based on shift schedule and zone type.

    Args:
        hour: Hour of day (0-23).
        day_of_week: Day of week (0=Monday, 6=Sunday).
        zone_type: Zone classification.

    Returns:
        Expected occupancy ratio (0.0 to 1.0).
    """
    ...


def _meeting_room_pattern(hour: int, day_of_week: int) -> float:
    """Model meeting room usage patterns.

    Args:
        hour: Hour of day.
        day_of_week: Day of week.

    Returns:
        Expected occupancy ratio.
    """
    ...


def _social_area_pattern(hour: int, day_of_week: int) -> float:
    """Model social area (copa, library) usage with lunch peak.

    Args:
        hour: Hour of day.
        day_of_week: Day of week.

    Returns:
        Expected occupancy ratio.
    """
    ...
