"""Synthetic energy consumption profiles.

Generates realistic kWh data for HVAC (60%), lighting (20%),
equipment (15%), and other (5%) with time-of-day, day-of-week,
and seasonal patterns. March in Aveiro climate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.thresholds import ENERGY_LIMITS


def generate_energy_data(
    zones: list[dict],
    days: int = 30,
    interval_min: int = 15,
    seed: int = 42,
    weather_df: pd.DataFrame | None = None,
    occupancy_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Generate energy consumption data for all zones.

    Args:
        zones: List of zone dicts with 'id', 'area_m2', 'has_hvac',
            'zone_type' keys.
        days: Number of days of history.
        interval_min: Time resolution in minutes.
        seed: Random seed.
        weather_df: Optional weather data for temperature-driven HVAC.
        occupancy_df: Optional occupancy data for load modulation.

    Returns:
        DataFrame with columns: timestamp, zone_id, hvac_kwh,
        lighting_kwh, equipment_kwh, other_kwh, total_kwh.
    """
    rng = np.random.default_rng(seed)
    intervals_per_day = 24 * 60 // interval_min  # 96 for 15-min
    n_timestamps = days * intervals_per_day

    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    timestamps = pd.date_range(
        start=start, periods=n_timestamps, freq=f"{interval_min}min"
    )

    hours = timestamps.hour + timestamps.minute / 60.0
    dow = timestamps.dayofweek
    is_weekend = dow >= 5

    # Pre-compute weather lookup (outdoor temp at each timestamp)
    outdoor_temps = _build_weather_lookup(timestamps, weather_df)

    # Pre-compute occupancy lookup per zone
    occ_lookup = _build_occupancy_lookup(timestamps, occupancy_df)

    all_records: list[pd.DataFrame] = []

    for zone in zones:
        zone_id = zone["id"]
        area = zone["area_m2"]
        has_hvac = zone.get("has_hvac", True)
        zone_type = zone["zone_type"]

        # Base energy budget per interval (kWh)
        # ENERGY_LIMITS defines warning thresholds; typical consumption is
        # ~3x these values on a normal business day to hit the 200-400 kWh/day
        # building target across ~1000 m² total area.
        limit = ENERGY_LIMITS.get(zone_type)
        limit_per_m2 = limit.max_kwh_per_m2_day if limit else 0.10
        daily_budget = limit_per_m2 * area * 6.0
        interval_budget = daily_budget / intervals_per_day

        # Get occupancy ratios for this zone
        occ_ratios = occ_lookup.get(zone_id, np.full(n_timestamps, 0.3))

        # Compute load factors vectorized
        hvac_factors = np.array(
            [_hvac_load_factor(h, d, 3) for h, d in zip(hours, dow)]
        )
        lighting_factors = np.array(
            [_lighting_load_factor(h, d) for h, d in zip(hours, dow)]
        )
        equipment_factors = np.array(
            [_equipment_load_factor(h, d) for h, d in zip(hours, dow)]
        )

        # Modulate HVAC by weather (heating demand)
        if has_hvac and outdoor_temps is not None:
            temp_diff = np.abs(outdoor_temps - 22.0)
            hvac_weather_boost = 1.0 + 0.03 * temp_diff
            hvac_factors *= hvac_weather_boost

        # Modulate by occupancy
        occ_boost = 0.3 + 0.7 * occ_ratios  # Range [0.3, 1.0]
        hvac_factors *= occ_boost
        lighting_factors *= occ_boost
        equipment_factors *= occ_boost

        # No HVAC for zones without it
        if not has_hvac:
            hvac_factors[:] = 0.0

        # Weekend reduction
        weekend_mask = (
            is_weekend.values if hasattr(is_weekend, "values") else is_weekend
        )
        hvac_factors[weekend_mask] *= 0.20
        lighting_factors[weekend_mask] *= 0.15
        equipment_factors[weekend_mask] *= 0.10

        # Zone-type specific equipment multiplier
        equip_mult = _zone_equipment_multiplier(zone_type)

        # Compute kWh per component
        hvac_kwh = interval_budget * 0.60 * hvac_factors
        lighting_kwh = interval_budget * 0.20 * lighting_factors
        equipment_kwh = interval_budget * 0.15 * equipment_factors * equip_mult
        other_kwh = np.full(n_timestamps, interval_budget * 0.05)
        other_kwh[weekend_mask] *= 0.30

        # Add realistic noise
        hvac_kwh *= 1 + rng.normal(0, 0.05, n_timestamps)
        lighting_kwh *= 1 + rng.normal(0, 0.03, n_timestamps)
        equipment_kwh *= 1 + rng.normal(0, 0.04, n_timestamps)
        other_kwh *= 1 + rng.normal(0, 0.02, n_timestamps)

        # Clip to non-negative
        hvac_kwh = np.clip(hvac_kwh, 0, None)
        lighting_kwh = np.clip(lighting_kwh, 0, None)
        equipment_kwh = np.clip(equipment_kwh, 0, None)
        other_kwh = np.clip(other_kwh, 0, None)

        total_kwh = hvac_kwh + lighting_kwh + equipment_kwh + other_kwh

        zone_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "zone_id": zone_id,
                "hvac_kwh": np.round(hvac_kwh, 4),
                "lighting_kwh": np.round(lighting_kwh, 4),
                "equipment_kwh": np.round(equipment_kwh, 4),
                "other_kwh": np.round(other_kwh, 4),
                "total_kwh": np.round(total_kwh, 4),
            }
        )
        all_records.append(zone_df)

    result = pd.concat(all_records, ignore_index=True)

    # Apply energy-meter sensor noise (additive, sigma=0.05 kWh)
    result = _apply_meter_noise(result, rng)

    # Inject anomalies
    result = _inject_energy_anomalies(result, zones, days, rng)

    return result


def _apply_meter_noise(
    df: pd.DataFrame, rng: np.random.Generator, sigma: float = 0.05
) -> pd.DataFrame:
    """Apply additive Gaussian noise simulating energy meter imprecision.

    Models the measurement noise of energy sub-meters (sigma=0.05 kWh)
    as specified in the sensor catalog for the energy_meter type.

    Args:
        df: Energy DataFrame with kWh columns.
        rng: NumPy random generator.
        sigma: Standard deviation of additive noise in kWh.

    Returns:
        DataFrame with meter noise applied, values clipped to non-negative.
    """
    result = df.copy()
    n = len(result)
    kwh_cols = ["hvac_kwh", "lighting_kwh", "equipment_kwh", "other_kwh"]
    for col in kwh_cols:
        if col in result.columns:
            result[col] = np.clip(result[col] + rng.normal(0, sigma, n), 0, None)
    result["total_kwh"] = result[kwh_cols].sum(axis=1).round(4)
    return result


def _build_weather_lookup(
    timestamps: pd.DatetimeIndex,
    weather_df: pd.DataFrame | None,
) -> np.ndarray | None:
    """Build outdoor temperature array aligned to energy timestamps.

    Args:
        timestamps: Energy data timestamps.
        weather_df: Weather DataFrame with 'timestamp' and 'outdoor_temp_c'.

    Returns:
        Array of outdoor temperatures or None.
    """
    if weather_df is None or weather_df.empty:
        return None
    weather_indexed = weather_df.set_index("timestamp")["outdoor_temp_c"]
    weather_reindexed = weather_indexed.reindex(timestamps, method="nearest")
    return weather_reindexed.values


def _build_occupancy_lookup(
    timestamps: pd.DatetimeIndex,
    occupancy_df: pd.DataFrame | None,
) -> dict[str, np.ndarray]:
    """Build per-zone occupancy ratio arrays aligned to energy timestamps.

    Args:
        timestamps: Energy data timestamps.
        occupancy_df: Occupancy DataFrame.

    Returns:
        Dict mapping zone_id to occupancy ratio arrays.
    """
    if occupancy_df is None or occupancy_df.empty:
        return {}
    lookup: dict[str, np.ndarray] = {}
    for zone_id, group in occupancy_df.groupby("zone_id"):
        occ_indexed = group.set_index("timestamp")["occupancy_ratio"]
        occ_reindexed = occ_indexed.reindex(timestamps, method="nearest")
        lookup[str(zone_id)] = occ_reindexed.fillna(0).values
    return lookup


def _zone_equipment_multiplier(zone_type: str) -> float:
    """Equipment load multiplier by zone type.

    Args:
        zone_type: Zone classification.

    Returns:
        Multiplier for equipment energy component.
    """
    multipliers = {
        "it_lab": 2.5,
        "office": 1.5,
        "production": 1.8,
        "auditorium": 1.3,
        "training": 1.0,
        "meeting": 1.0,
        "multipurpose": 1.1,
        "dojo": 0.8,
        "library": 1.0,
        "social": 0.7,
        "reception": 0.8,
        "circulation": 0.3,
        "storage": 0.1,
        "sanitary": 0.2,
        "archive": 0.1,
    }
    return multipliers.get(zone_type, 1.0)


def _inject_energy_anomalies(
    df: pd.DataFrame,
    zones: list[dict],
    days: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Inject 3-5 energy anomalies per week into the data.

    Anomaly types:
    - HVAC stuck on: full HVAC load during night/weekend
    - Equipment spike: 3-5x equipment load for 1-3 hours
    - Unusual night load: full lighting during night hours

    Args:
        df: Energy DataFrame.
        zones: Zone list.
        days: Number of days.
        rng: Random generator.

    Returns:
        DataFrame with injected anomalies.
    """
    result = df.copy()
    hvac_zones = [z for z in zones if z.get("has_hvac", True)]
    n_weeks = max(1, days // 7)

    for _ in range(n_weeks):
        n_anomalies = rng.integers(3, 6)
        for _ in range(n_anomalies):
            anomaly_type = rng.choice(["hvac_stuck", "equip_spike", "night_load"])
            target_zone = rng.choice(hvac_zones)
            zone_id = target_zone["id"]

            # Pick a random day
            day_offset = rng.integers(0, days)
            base_ts = pd.Timestamp.now().normalize() - pd.Timedelta(
                days=days - day_offset
            )

            zone_mask = result["zone_id"] == zone_id

            if anomaly_type == "hvac_stuck":
                # HVAC stuck on during night (22h-6h): 6-12 hour duration
                start_ts = base_ts + pd.Timedelta(hours=22)
                duration_h = rng.integers(6, 13)
                end_ts = start_ts + pd.Timedelta(hours=int(duration_h))
                time_mask = (result["timestamp"] >= start_ts) & (
                    result["timestamp"] < end_ts
                )
                mask = zone_mask & time_mask
                if mask.sum() > 0:
                    limit = ENERGY_LIMITS.get(target_zone["zone_type"])
                    peak = (
                        (limit.max_kwh_per_m2_day if limit else 0.10)
                        * target_zone["area_m2"]
                        / 96
                    )
                    result.loc[mask, "hvac_kwh"] = peak * 0.60 * rng.uniform(0.8, 1.0)

            elif anomaly_type == "equip_spike":
                # Equipment spike during business hours
                start_h = rng.integers(8, 18)
                duration_h = rng.integers(1, 4)
                start_ts = base_ts + pd.Timedelta(hours=int(start_h))
                end_ts = start_ts + pd.Timedelta(hours=int(duration_h))
                time_mask = (result["timestamp"] >= start_ts) & (
                    result["timestamp"] < end_ts
                )
                mask = zone_mask & time_mask
                if mask.sum() > 0:
                    spike_factor = rng.uniform(3, 5)
                    result.loc[mask, "equipment_kwh"] *= spike_factor

            else:  # night_load
                # Full lighting during night
                start_ts = base_ts + pd.Timedelta(hours=23)
                end_ts = start_ts + pd.Timedelta(hours=rng.integers(3, 7))
                time_mask = (result["timestamp"] >= start_ts) & (
                    result["timestamp"] < end_ts
                )
                mask = zone_mask & time_mask
                if mask.sum() > 0:
                    limit = ENERGY_LIMITS.get(target_zone["zone_type"])
                    peak = (
                        (limit.max_kwh_per_m2_day if limit else 0.10)
                        * target_zone["area_m2"]
                        / 96
                    )
                    result.loc[mask, "lighting_kwh"] = (
                        peak * 0.20 * rng.uniform(0.7, 1.0)
                    )

    # Recompute total
    result["total_kwh"] = (
        result["hvac_kwh"]
        + result["lighting_kwh"]
        + result["equipment_kwh"]
        + result["other_kwh"]
    )
    result["total_kwh"] = result["total_kwh"].round(4)

    return result


def _hvac_load_factor(hour: float, day_of_week: int, month: int) -> float:
    """Calculate HVAC load factor based on temporal patterns.

    Args:
        hour: Hour of day (0-23, fractional).
        day_of_week: Day of week (0=Monday, 6=Sunday).
        month: Month (1-12).

    Returns:
        Load factor between 0.0 and 1.0.
    """
    # Night: minimal (just frost protection)
    if hour < 5 or hour >= 22:
        return 0.05

    # Early morning ramp-up
    if 5 <= hour < 7:
        return 0.1 + 0.4 * (hour - 5) / 2

    # Morning peak
    if 7 <= hour < 12:
        return 0.8 + 0.1 * np.sin(np.pi * (hour - 7) / 5)

    # Lunch dip
    if 12 <= hour < 13:
        return 0.65

    # Afternoon peak
    if 13 <= hour < 17:
        return 0.85

    # Evening ramp-down
    if 17 <= hour < 22:
        return 0.85 - 0.6 * (hour - 17) / 5

    return 0.1


def _lighting_load_factor(hour: float, day_of_week: int) -> float:
    """Calculate lighting load factor.

    Args:
        hour: Hour of day (0-23, fractional).
        day_of_week: Day of week.

    Returns:
        Load factor between 0.0 and 1.0.
    """
    # Night: emergency lighting only
    if hour < 6 or hour >= 22:
        return 0.05

    # Morning ramp
    if 6 <= hour < 7:
        return 0.2 + 0.6 * (hour - 6)

    # Business hours: full with natural light variation
    if 7 <= hour < 12:
        # Less artificial light near midday due to sunlight
        return 0.8 - 0.15 * np.sin(np.pi * (hour - 7) / 5)

    if 12 <= hour < 14:
        return 0.60  # Midday natural light

    if 14 <= hour < 18:
        return 0.75 + 0.15 * (hour - 14) / 4  # Increasing as sun sets

    # Evening
    if 18 <= hour < 22:
        return 0.9 - 0.6 * (hour - 18) / 4

    return 0.05


def _equipment_load_factor(hour: float, day_of_week: int) -> float:
    """Calculate equipment load factor.

    Args:
        hour: Hour of day (0-23, fractional).
        day_of_week: Day of week.

    Returns:
        Load factor between 0.0 and 1.0.
    """
    # Standby at night
    if hour < 6 or hour >= 22:
        return 0.05

    # Morning startup
    if 6 <= hour < 7:
        return 0.15 + 0.5 * (hour - 6)

    # Business hours
    if 7 <= hour < 12:
        return 0.75

    # Lunch dip
    if 12 <= hour < 13:
        return 0.50

    # Afternoon
    if 13 <= hour < 18:
        return 0.70

    # Evening wind-down
    if 18 <= hour < 22:
        return 0.70 - 0.55 * (hour - 18) / 4

    return 0.05
