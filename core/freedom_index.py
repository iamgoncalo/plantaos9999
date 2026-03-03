"""Per-zone Freedom Index (health score 0-100).

Computes a composite health score for each zone based on comfort compliance,
energy efficiency, occupancy patterns, and anomaly rates.
Higher score = healthier zone.

Weights:
  - Comfort compliance: 40%
  - Energy efficiency: 30%
  - Occupancy health: 20%
  - Anomaly rate: 10%
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.building import get_monitored_zones, get_zone_by_id
from config.thresholds import COMFORT_BANDS, ENERGY_LIMITS
from data.store import store


# Weight constants
WEIGHT_COMFORT = 0.40
WEIGHT_ENERGY = 0.30
WEIGHT_OCCUPANCY = 0.20
WEIGHT_ANOMALY = 0.10


def compute_zone_freedom(zone_id: str) -> float:
    """Compute the Freedom Index for a single zone.

    Args:
        zone_id: Zone to score.

    Returns:
        Score from 0.0 (poor) to 100.0 (excellent).
    """
    comfort = _comfort_score(zone_id)
    energy = _energy_score(zone_id)
    occupancy = _occupancy_score(zone_id)
    anomaly = _anomaly_score(zone_id)

    score = (
        WEIGHT_COMFORT * comfort
        + WEIGHT_ENERGY * energy
        + WEIGHT_OCCUPANCY * occupancy
        + WEIGHT_ANOMALY * anomaly
    )

    return round(min(100.0, max(0.0, score)), 1)


def compute_building_freedom() -> dict[str, float]:
    """Compute Freedom Index for all zones in the building.

    Returns:
        Dict mapping zone_id to Freedom Index score.
    """
    results: dict[str, float] = {}
    for zone in get_monitored_zones():
        results[zone.id] = compute_zone_freedom(zone.id)
    return results


def _comfort_score(zone_id: str) -> float:
    """Score comfort compliance (0-100).

    Checks how well temperature, humidity, CO2, and lux stay within
    optimal bands.

    Args:
        zone_id: Zone identifier.

    Returns:
        Comfort subscore.
    """
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df is None or comfort_df.empty:
        return 50.0  # Neutral default

    # Use last 24 hours of data
    if "timestamp" in comfort_df.columns:
        cutoff = comfort_df["timestamp"].max() - pd.Timedelta(hours=24)
        comfort_df = comfort_df[comfort_df["timestamp"] >= cutoff]

    if comfort_df.empty:
        return 50.0

    metrics_in_band = []

    # Temperature: optimal 20-24°C
    if "temperature_c" in comfort_df.columns:
        temp = comfort_df["temperature_c"]
        band = COMFORT_BANDS.get("temperature")
        if band:
            in_optimal = (
                (temp >= band.min_optimal) & (temp <= band.max_optimal)
            ).mean()
            metrics_in_band.append(in_optimal)

    # Humidity: optimal 40-60%
    if "humidity_pct" in comfort_df.columns:
        hum = comfort_df["humidity_pct"]
        band = COMFORT_BANDS.get("humidity")
        if band:
            in_optimal = ((hum >= band.min_optimal) & (hum <= band.max_optimal)).mean()
            metrics_in_band.append(in_optimal)

    # CO2: optimal 400-800 ppm
    if "co2_ppm" in comfort_df.columns:
        co2 = comfort_df["co2_ppm"]
        band = COMFORT_BANDS.get("co2")
        if band:
            in_optimal = ((co2 >= band.min_optimal) & (co2 <= band.max_optimal)).mean()
            metrics_in_band.append(in_optimal)

    # Illuminance: optimal 300-500 lux
    if "illuminance_lux" in comfort_df.columns:
        lux = comfort_df["illuminance_lux"]
        band = COMFORT_BANDS.get("illuminance")
        if band:
            in_optimal = ((lux >= band.min_optimal) & (lux <= band.max_optimal)).mean()
            metrics_in_band.append(in_optimal)

    if not metrics_in_band:
        return 50.0

    return float(np.mean(metrics_in_band) * 100)


def _energy_score(zone_id: str) -> float:
    """Score energy efficiency (0-100).

    Compares actual consumption to thresholds for the zone type,
    normalized by area.

    Args:
        zone_id: Zone identifier.

    Returns:
        Energy subscore.
    """
    zone = get_zone_by_id(zone_id)
    if zone is None:
        return 50.0

    energy_df = store.get_zone_data("energy", zone_id)
    if energy_df is None or energy_df.empty:
        return 50.0

    # Use last 24 hours
    if "timestamp" in energy_df.columns:
        cutoff = energy_df["timestamp"].max() - pd.Timedelta(hours=24)
        energy_df = energy_df[energy_df["timestamp"] >= cutoff]

    if energy_df.empty or "total_kwh" not in energy_df.columns:
        return 50.0

    daily_kwh = energy_df["total_kwh"].sum()
    area = zone.area_m2

    if area <= 0:
        return 50.0

    kwh_per_m2 = daily_kwh / area
    limit = ENERGY_LIMITS.get(zone.zone_type.value)
    max_kwh_per_m2 = limit.max_kwh_per_m2_day if limit else 0.15

    # Score: 100 when at 0%, 0 when at 200% of limit
    ratio = kwh_per_m2 / max_kwh_per_m2 if max_kwh_per_m2 > 0 else 1.0
    score = max(0.0, 100.0 * (1.0 - ratio / 2.0))

    return min(100.0, score)


def _occupancy_score(zone_id: str) -> float:
    """Score occupancy health (0-100).

    Evaluates utilization rate, overcrowding incidents, and
    usage pattern regularity.

    Args:
        zone_id: Zone identifier.

    Returns:
        Occupancy subscore.
    """
    zone = get_zone_by_id(zone_id)
    if zone is None or zone.capacity == 0:
        return 75.0  # Non-capacity zones get neutral score

    occ_df = store.get_zone_data("occupancy", zone_id)
    if occ_df is None or occ_df.empty:
        return 50.0

    # Use last 24 hours
    if "timestamp" in occ_df.columns:
        cutoff = occ_df["timestamp"].max() - pd.Timedelta(hours=24)
        occ_df = occ_df[occ_df["timestamp"] >= cutoff]

    if occ_df.empty or "occupancy_ratio" not in occ_df.columns:
        return 50.0

    ratios = occ_df["occupancy_ratio"]

    # Penalize overcrowding (ratio > 1.0)
    overcrowding_pct = (ratios > 1.0).mean()

    # Penalize very low utilization during business hours (< 10%)
    if "timestamp" in occ_df.columns:
        hours = pd.to_datetime(occ_df["timestamp"]).dt.hour
        business = (hours >= 6) & (hours < 22)
        business_ratios = ratios[business]
        underuse_pct = (
            (business_ratios < 0.10).mean() if len(business_ratios) > 0 else 0
        )
    else:
        underuse_pct = 0

    # Base score from reasonable utilization (30-80% is ideal)
    mean_ratio = ratios.mean()
    if 0.3 <= mean_ratio <= 0.8:
        base = 90.0
    elif 0.1 <= mean_ratio < 0.3:
        base = 70.0
    elif 0.8 < mean_ratio <= 1.0:
        base = 75.0
    else:
        base = 60.0

    # Deductions
    score = base - overcrowding_pct * 50 - underuse_pct * 20

    return max(0.0, min(100.0, score))


def _anomaly_score(zone_id: str) -> float:
    """Score based on anomaly frequency (0-100).

    Lower anomaly rate = higher score. Uses z-score detection on the
    last 24 hours of comfort data as a quick proxy.

    Args:
        zone_id: Zone identifier.

    Returns:
        Anomaly subscore.
    """
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df is None or comfort_df.empty:
        return 80.0  # No data = assume mostly OK

    # Use last 24 hours
    if "timestamp" in comfort_df.columns:
        cutoff = comfort_df["timestamp"].max() - pd.Timedelta(hours=24)
        comfort_df = comfort_df[comfort_df["timestamp"] >= cutoff]

    if comfort_df.empty:
        return 80.0

    # Count readings that are outside 2σ for each metric
    anomaly_count = 0
    total_readings = 0

    for col in ["temperature_c", "humidity_pct", "co2_ppm", "illuminance_lux"]:
        if col not in comfort_df.columns:
            continue
        series = comfort_df[col].dropna()
        if series.empty or series.std() < 1e-10:
            continue
        total_readings += len(series)
        mean = series.mean()
        std = series.std()
        anomaly_count += int(((series - mean).abs() > 2 * std).sum())

    if total_readings == 0:
        return 80.0

    anomaly_rate = anomaly_count / total_readings
    # Score: 100 when 0% anomalies, 0 when >10% anomalies
    score = 100.0 * (1.0 - min(1.0, anomaly_rate * 10))

    return max(0.0, score)
