"""Synthetic comfort metric profiles.

Generates temperature, humidity, CO2, and illuminance data per zone
with realistic diurnal patterns, occupancy-driven variations, and
March-in-Aveiro climate influence (8-18°C outdoor, 60-85% humidity).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_comfort_data(
    zones: list[dict],
    days: int = 30,
    interval_min: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate comfort metrics for all zones.

    Args:
        zones: List of zone dicts with 'id', 'capacity', 'has_sensors' keys.
        days: Number of days of history.
        interval_min: Time resolution in minutes.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, zone_id, temperature_c,
        humidity_pct, co2_ppm, illuminance_lux.
    """
    ...


def _temperature_profile(
    hour: int,
    month: int,
    occupancy_ratio: float,
    outdoor_temp: float,
) -> float:
    """Model indoor temperature considering time, season, and occupancy.

    Args:
        hour: Hour of day.
        month: Month of year.
        occupancy_ratio: Current occupancy as fraction of capacity.
        outdoor_temp: Outdoor temperature in °C.

    Returns:
        Temperature in degrees Celsius.
    """
    ...


def _humidity_profile(
    hour: int,
    occupancy_ratio: float,
    outdoor_humidity: float,
) -> float:
    """Model indoor humidity based on occupancy and outdoor conditions.

    Args:
        hour: Hour of day.
        occupancy_ratio: Occupancy fraction.
        outdoor_humidity: Outdoor humidity percentage.

    Returns:
        Humidity percentage.
    """
    ...


def _co2_profile(
    hour: int,
    occupancy_ratio: float,
    ventilation_rate: float = 1.0,
) -> float:
    """Model CO2 concentration based on occupancy and ventilation.

    Args:
        hour: Hour of day.
        occupancy_ratio: Occupancy fraction.
        ventilation_rate: Ventilation effectiveness (0-1).

    Returns:
        CO2 concentration in ppm.
    """
    ...


def _illuminance_profile(hour: int, has_windows: bool = True) -> float:
    """Model illuminance based on time of day and window presence.

    Args:
        hour: Hour of day.
        has_windows: Whether the zone has windows.

    Returns:
        Illuminance in lux.
    """
    ...
