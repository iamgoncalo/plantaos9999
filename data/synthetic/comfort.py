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
    weather_df: pd.DataFrame | None = None,
    occupancy_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Generate comfort metrics for all zones.

    Args:
        zones: List of zone dicts with 'id', 'capacity', 'has_sensors',
            'zone_type' keys.
        days: Number of days of history.
        interval_min: Time resolution in minutes.
        seed: Random seed.
        weather_df: Optional weather data for outdoor influence.
        occupancy_df: Optional occupancy data for CO2/temperature modulation.

    Returns:
        DataFrame with columns: timestamp, zone_id, temperature_c,
        humidity_pct, co2_ppm, illuminance_lux.
    """
    rng = np.random.default_rng(seed + 10)
    intervals_per_day = 24 * 60 // interval_min  # 288 for 5-min
    n_timestamps = days * intervals_per_day

    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    timestamps = pd.date_range(
        start=start, periods=n_timestamps, freq=f"{interval_min}min"
    )

    hours = timestamps.hour + timestamps.minute / 60.0
    dow = timestamps.dayofweek
    is_weekend = dow >= 5

    # Pre-compute weather arrays at comfort resolution
    outdoor_temp_arr, outdoor_hum_arr, is_raining_arr = _build_weather_arrays(
        timestamps, weather_df
    )

    # Pre-compute occupancy lookup
    occ_lookup = _build_occ_lookup(timestamps, occupancy_df)

    # Monitored zones only
    sensor_zones = [z for z in zones if z.get("has_sensors", True)]

    all_records: list[pd.DataFrame] = []

    for zone in sensor_zones:
        zone_id = zone["id"]
        capacity = zone.get("capacity", 0)
        zone_type = zone["zone_type"]
        has_windows = zone_type not in ("storage", "sanitary", "archive")

        # Get occupancy for this zone
        occ_ratios = occ_lookup.get(zone_id, np.zeros(n_timestamps))
        occ_counts = occ_ratios * max(capacity, 1)

        # --- Temperature ---
        temp = np.zeros(n_timestamps)
        for i in range(n_timestamps):
            temp[i] = _temperature_profile(
                hours[i], 3, occ_ratios[i], outdoor_temp_arr[i]
            )
        # HVAC off at night/weekend: drift toward outdoor
        for i in range(n_timestamps):
            h = hours[i]
            if h < 6 or h >= 22 or is_weekend[i]:
                # Partial drift toward outdoor (building thermal mass)
                drift_factor = 0.3 if is_weekend[i] and 8 <= h < 18 else 0.5
                temp[i] = (
                    temp[i] * (1 - drift_factor) + outdoor_temp_arr[i] * drift_factor
                )
        temp += rng.normal(0, 0.2, n_timestamps)  # sensor noise (sigma=0.2)

        # --- Humidity ---
        humidity = np.zeros(n_timestamps)
        for i in range(n_timestamps):
            humidity[i] = _humidity_profile(hours[i], occ_ratios[i], outdoor_hum_arr[i])
        humidity[is_raining_arr] += rng.uniform(3, 8, is_raining_arr.sum())
        humidity += rng.normal(0, 0.5, n_timestamps)  # sensor noise (sigma=0.5)
        humidity = np.clip(humidity, 30, 80)

        # --- CO2 ---
        co2 = np.zeros(n_timestamps)
        for i in range(n_timestamps):
            ventilation = 1.0 if 6 <= hours[i] < 22 and not is_weekend[i] else 0.3
            co2[i] = _co2_profile(hours[i], occ_counts[i], ventilation)
        co2 += rng.normal(0, 15, n_timestamps)
        co2 = np.clip(co2, 350, 2000)

        # --- Illuminance ---
        lux = np.zeros(n_timestamps)
        for i in range(n_timestamps):
            lux[i] = _illuminance_profile(hours[i], has_windows)
        # Modulate by occupancy (lights on when occupied)
        for i in range(n_timestamps):
            if occ_ratios[i] < 0.05 and 6 <= hours[i] < 22:
                lux[i] *= 0.15  # Empty room, lights mostly off
        lux += rng.normal(0, 5.0, n_timestamps)  # sensor noise (sigma=5.0)
        lux = np.clip(lux, 0, 1200)

        zone_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "zone_id": zone_id,
                "temperature_c": np.round(temp, 1),
                "humidity_pct": np.round(humidity, 1),
                "co2_ppm": np.round(co2, 0).astype(int),
                "illuminance_lux": np.round(lux, 0).astype(int),
            }
        )
        all_records.append(zone_df)

    result = pd.concat(all_records, ignore_index=True)

    # Apply sensor-model noise as a final pass
    result = _apply_noise(result, rng)

    # Inject comfort anomalies
    result = _inject_comfort_anomalies(
        result, sensor_zones, days, rng, outdoor_temp_arr
    )

    return result


def _apply_noise(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Apply sensor-model Gaussian noise to comfort metrics.

    Adds realistic measurement noise matching sensor hardware specs:
    - temperature: sigma=0.2 C
    - humidity: sigma=0.5 %
    - co2: sigma=15.0 ppm
    - illuminance: sigma=5.0 lux

    Args:
        df: Comfort DataFrame with metric columns.
        rng: NumPy random generator.

    Returns:
        DataFrame with sensor noise applied and values clipped to
        physically valid ranges.
    """
    result = df.copy()
    n = len(result)
    noise_spec: dict[str, tuple[float, float, float]] = {
        # column: (sigma, clip_min, clip_max)
        "temperature_c": (0.2, -10.0, 50.0),
        "humidity_pct": (0.5, 0.0, 100.0),
        "co2_ppm": (15.0, 350.0, 5000.0),
        "illuminance_lux": (5.0, 0.0, 10000.0),
    }
    for col, (sigma, lo, hi) in noise_spec.items():
        if col in result.columns:
            result[col] = np.clip(result[col] + rng.normal(0, sigma, n), lo, hi)
    return result


def _build_weather_arrays(
    timestamps: pd.DatetimeIndex,
    weather_df: pd.DataFrame | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build weather arrays aligned to comfort timestamps.

    Args:
        timestamps: Comfort data timestamps.
        weather_df: Weather DataFrame.

    Returns:
        Tuple of (outdoor_temp, outdoor_humidity, is_raining) arrays.
    """
    n = len(timestamps)
    if weather_df is None or weather_df.empty:
        # Synthetic fallback: simple sinusoidal
        hours = timestamps.hour + timestamps.minute / 60.0
        temp = 13.0 - 5.0 * np.cos(2 * np.pi * (hours - 5) / 24)
        hum = np.full(n, 70.0)
        rain = np.zeros(n, dtype=bool)
        return temp, hum, rain

    weather_indexed = weather_df.set_index("timestamp")
    temp = (
        weather_indexed["outdoor_temp_c"].reindex(timestamps, method="nearest").values
    )
    hum = (
        weather_indexed["outdoor_humidity_pct"]
        .reindex(timestamps, method="nearest")
        .values
    )
    rain = (
        weather_indexed["is_raining"]
        .reindex(timestamps, method="nearest")
        .fillna(False)
        .values
    )
    return temp, hum, rain.astype(bool)


def _build_occ_lookup(
    timestamps: pd.DatetimeIndex,
    occupancy_df: pd.DataFrame | None,
) -> dict[str, np.ndarray]:
    """Build per-zone occupancy ratio arrays at comfort resolution.

    Args:
        timestamps: Comfort data timestamps.
        occupancy_df: Occupancy DataFrame.

    Returns:
        Dict mapping zone_id to occupancy ratio arrays.
    """
    if occupancy_df is None or occupancy_df.empty:
        return {}
    lookup: dict[str, np.ndarray] = {}
    for zone_id, group in occupancy_df.groupby("zone_id"):
        occ = group.set_index("timestamp")["occupancy_ratio"]
        occ_aligned = occ.reindex(timestamps, method="nearest").fillna(0).values
        lookup[str(zone_id)] = occ_aligned
    return lookup


def _inject_comfort_anomalies(
    df: pd.DataFrame,
    zones: list[dict],
    days: int,
    rng: np.random.Generator,
    outdoor_temps: np.ndarray,
) -> pd.DataFrame:
    """Inject 2-3 comfort anomalies per week.

    Types:
    - HVAC failure: temperature drifts toward outdoor for 2-6 hours
    - Window left open: humidity spikes, temp drifts, CO2 drops

    Args:
        df: Comfort DataFrame.
        zones: Monitored zone list.
        days: Number of days.
        rng: Random generator.
        outdoor_temps: Outdoor temperature array.

    Returns:
        DataFrame with injected anomalies.
    """
    result = df.copy()
    n_weeks = max(1, days // 7)
    intervals_per_day = 288  # 5-min

    for _ in range(n_weeks):
        n_anomalies = rng.integers(2, 4)
        for _ in range(n_anomalies):
            anomaly_type = rng.choice(["hvac_failure", "window_open"])
            target = rng.choice(zones)
            zone_id = target["id"]

            day_offset = rng.integers(0, days)
            base_ts = pd.Timestamp.now().normalize() - pd.Timedelta(
                days=days - day_offset
            )

            zone_mask = result["zone_id"] == zone_id

            if anomaly_type == "hvac_failure":
                # HVAC fails during business hours: temp drifts for 2-6h
                start_h = rng.integers(9, 16)
                duration_h = rng.integers(2, 7)
                start_ts = base_ts + pd.Timedelta(hours=int(start_h))
                end_ts = start_ts + pd.Timedelta(hours=int(duration_h))
                time_mask = (result["timestamp"] >= start_ts) & (
                    result["timestamp"] < end_ts
                )
                mask = zone_mask & time_mask
                affected = mask.sum()
                if affected > 0:
                    # Temperature drifts toward outdoor
                    drift = np.linspace(0, 1, affected)
                    outdoor_avg = (
                        np.mean(
                            outdoor_temps[
                                day_offset * intervals_per_day : min(
                                    (day_offset + 1) * intervals_per_day,
                                    len(outdoor_temps),
                                )
                            ]
                        )
                        if day_offset * intervals_per_day < len(outdoor_temps)
                        else 12.0
                    )
                    current_temps = result.loc[mask, "temperature_c"].values
                    drifted = (
                        current_temps * (1 - drift * 0.6) + outdoor_avg * drift * 0.6
                    )
                    result.loc[mask, "temperature_c"] = np.round(drifted, 1)

            else:  # window_open
                # Window open: humidity spikes, temp drifts, CO2 drops
                start_h = rng.integers(8, 17)
                duration_h = rng.integers(1, 4)
                start_ts = base_ts + pd.Timedelta(hours=int(start_h))
                end_ts = start_ts + pd.Timedelta(hours=int(duration_h))
                time_mask = (result["timestamp"] >= start_ts) & (
                    result["timestamp"] < end_ts
                )
                mask = zone_mask & time_mask
                affected = mask.sum()
                if affected > 0:
                    result.loc[mask, "humidity_pct"] += rng.uniform(15, 25)
                    result.loc[mask, "humidity_pct"] = (
                        result.loc[mask, "humidity_pct"].clip(30, 95).round(1)
                    )
                    # CO2 drops toward outdoor level
                    co2_vals = result.loc[mask, "co2_ppm"].values * rng.uniform(
                        0.5, 0.7
                    )
                    result.loc[mask, "co2_ppm"] = np.clip(co2_vals, 350, 2000).astype(
                        int
                    )
                    # Temp drifts toward outdoor
                    result.loc[mask, "temperature_c"] += rng.uniform(-3, -1)

    return result


def _temperature_profile(
    hour: float,
    month: int,
    occupancy_ratio: float,
    outdoor_temp: float,
) -> float:
    """Model indoor temperature considering time, season, and occupancy.

    Args:
        hour: Hour of day (fractional).
        month: Month of year.
        occupancy_ratio: Current occupancy as fraction of capacity.
        outdoor_temp: Outdoor temperature in °C.

    Returns:
        Temperature in degrees Celsius.
    """
    # HVAC setpoint
    setpoint = 22.0

    # Business hours: HVAC maintains setpoint
    if 6 <= hour < 22:
        base = setpoint
        # Body heat from occupants
        base += occupancy_ratio * 2.5
        # Outdoor influence (damped by insulation)
        base += (outdoor_temp - setpoint) * 0.10
        # Slight daily warming trend
        base += 0.3 * np.sin(np.pi * (hour - 6) / 16)
        return base

    # Night: no HVAC, drift toward outdoor
    night_drift = 0.4  # Building retains some heat
    return setpoint * (1 - night_drift) + outdoor_temp * night_drift


def _humidity_profile(
    hour: float,
    occupancy_ratio: float,
    outdoor_humidity: float,
) -> float:
    """Model indoor humidity based on occupancy and outdoor conditions.

    Args:
        hour: Hour of day (fractional).
        occupancy_ratio: Occupancy fraction.
        outdoor_humidity: Outdoor humidity percentage.

    Returns:
        Humidity percentage.
    """
    # Base indoor humidity controlled by HVAC
    base = 50.0

    if 6 <= hour < 22:
        # Occupancy adds moisture (breathing, body)
        base += occupancy_ratio * 10.0
        # Outdoor influence (limited by HVAC dehumidification)
        base += (outdoor_humidity - 70) * 0.15
    else:
        # Night: drift toward outdoor
        base = 50.0 * 0.5 + outdoor_humidity * 0.5

    return np.clip(base, 35, 80)


def _co2_profile(
    hour: float,
    occupant_count: float,
    ventilation_rate: float = 1.0,
) -> float:
    """Model CO2 concentration based on occupancy and ventilation.

    Args:
        hour: Hour of day (fractional).
        occupant_count: Number of occupants in the zone.
        ventilation_rate: Ventilation effectiveness (0-1).

    Returns:
        CO2 concentration in ppm.
    """
    outdoor_co2 = 400.0

    # Each person adds ~40 ppm (steady state with some ventilation)
    person_contribution = 40.0 * occupant_count

    # Ventilation dilutes CO2
    dilution = 0.3 + 0.7 * ventilation_rate

    co2 = outdoor_co2 + person_contribution * (1 - dilution * 0.5)

    return max(co2, outdoor_co2)


def _illuminance_profile(hour: float, has_windows: bool = True) -> float:
    """Model illuminance based on time of day and window presence.

    Args:
        hour: Hour of day (fractional).
        has_windows: Whether the zone has windows.

    Returns:
        Illuminance in lux.
    """
    # Night: emergency lighting only
    if hour < 6 or hour >= 22:
        return 10.0

    # Artificial lighting component (business hours)
    artificial = 0.0
    if 6 <= hour < 7:
        artificial = 200 + 200 * (hour - 6)
    elif 7 <= hour < 21:
        artificial = 400.0
    elif 21 <= hour < 22:
        artificial = 400 * (22 - hour)

    # Natural light component (for windowed zones)
    natural = 0.0
    if has_windows:
        sunrise, sunset = 7.0, 19.0
        if sunrise <= hour <= sunset:
            solar_phase = np.pi * (hour - sunrise) / (sunset - sunrise)
            natural = 350 * np.sin(solar_phase)

    return artificial + natural
