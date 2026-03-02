"""Rolling statistical baselines.

Computes rolling mean, standard deviation, and percentile baselines
for all metrics, enabling deviation detection and trend analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel

from data.store import store


# Metric → (dataset_name, column_name)
_METRIC_MAP: dict[str, tuple[str, str]] = {
    "temperature": ("comfort", "temperature_c"),
    "temperature_c": ("comfort", "temperature_c"),
    "humidity": ("comfort", "humidity_pct"),
    "humidity_pct": ("comfort", "humidity_pct"),
    "co2": ("comfort", "co2_ppm"),
    "co2_ppm": ("comfort", "co2_ppm"),
    "illuminance": ("comfort", "illuminance_lux"),
    "illuminance_lux": ("comfort", "illuminance_lux"),
    "energy": ("energy", "total_kwh"),
    "total_kwh": ("energy", "total_kwh"),
    "hvac_kwh": ("energy", "hvac_kwh"),
    "lighting_kwh": ("energy", "lighting_kwh"),
    "equipment_kwh": ("energy", "equipment_kwh"),
    "occupancy": ("occupancy", "occupant_count"),
    "occupant_count": ("occupancy", "occupant_count"),
    "occupancy_ratio": ("occupancy", "occupancy_ratio"),
}


class BaselineResult(BaseModel):
    """Result of a baseline computation for a metric."""

    zone_id: str
    metric: str
    mean: float
    std: float
    p5: float = 0.0
    p25: float
    p50: float = 0.0
    p75: float
    p95: float = 0.0
    window_days: int
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    confidence: float = 0.0


def compute_rolling_baseline(
    series: pd.Series,
    window: int = 7,
) -> BaselineResult:
    """Compute rolling statistical baseline for a time series.

    Args:
        series: Time-indexed series of metric values.
        window: Rolling window size in days.

    Returns:
        BaselineResult with mean, std, and percentiles.
    """
    if series.empty:
        return BaselineResult(
            zone_id="unknown", metric="unknown",
            mean=0, std=0, p25=0, p75=0, window_days=window,
        )

    values = series.dropna()
    if values.empty:
        return BaselineResult(
            zone_id="unknown", metric="unknown",
            mean=0, std=0, p25=0, p75=0, window_days=window,
        )

    mean_val = float(values.mean())
    std_val = float(values.std())
    p5 = float(np.percentile(values, 5))
    p25 = float(np.percentile(values, 25))
    p50 = float(np.percentile(values, 50))
    p75 = float(np.percentile(values, 75))
    p95 = float(np.percentile(values, 95))

    # Bounds: mean ± 2σ
    lower = mean_val - 2 * std_val
    upper = mean_val + 2 * std_val

    # Confidence based on sample size (more data = higher confidence)
    n = len(values)
    confidence = min(1.0, n / (window * 96))  # 96 intervals/day at 15-min

    return BaselineResult(
        zone_id=series.name if hasattr(series, "name") and isinstance(series.name, str) else "unknown",
        metric="unknown",
        mean=round(mean_val, 4),
        std=round(std_val, 4),
        p5=round(p5, 4),
        p25=round(p25, 4),
        p50=round(p50, 4),
        p75=round(p75, 4),
        p95=round(p95, 4),
        window_days=window,
        lower_bound=round(lower, 4),
        upper_bound=round(upper, 4),
        confidence=round(confidence, 3),
    )


def get_baseline_for_zone(
    zone_id: str,
    metric: str,
    window_days: int = 7,
) -> BaselineResult:
    """Get the baseline for a specific zone and metric.

    Fetches data from the DataStore and computes the rolling baseline.

    Args:
        zone_id: Zone identifier.
        metric: Metric name (e.g., 'temperature', 'total_kwh').
        window_days: Number of days for the rolling window.

    Returns:
        BaselineResult for the zone-metric combination.
    """
    mapping = _METRIC_MAP.get(metric)
    if mapping is None:
        logger.warning(f"Unknown metric '{metric}' for baseline")
        return BaselineResult(
            zone_id=zone_id, metric=metric,
            mean=0, std=0, p25=0, p75=0, window_days=window_days,
        )

    dataset_name, column_name = mapping

    zone_df = store.get_zone_data(dataset_name, zone_id)
    if zone_df is None or zone_df.empty:
        logger.debug(f"No data for zone '{zone_id}' in '{dataset_name}'")
        return BaselineResult(
            zone_id=zone_id, metric=metric,
            mean=0, std=0, p25=0, p75=0, window_days=window_days,
        )

    if column_name not in zone_df.columns:
        logger.warning(f"Column '{column_name}' not in '{dataset_name}'")
        return BaselineResult(
            zone_id=zone_id, metric=metric,
            mean=0, std=0, p25=0, p75=0, window_days=window_days,
        )

    # Filter to window
    if "timestamp" in zone_df.columns:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=window_days)
        zone_df = zone_df[zone_df["timestamp"] >= cutoff]

    series = zone_df[column_name]
    result = compute_rolling_baseline(series, window=window_days)
    result.zone_id = zone_id
    result.metric = metric
    return result


def compute_time_of_day_baseline(
    df: pd.DataFrame,
    value_column: str,
    zone_id: str | None = None,
) -> pd.DataFrame:
    """Compute typical values by time-of-day and day-of-week.

    Args:
        df: Input DataFrame with 'timestamp' column.
        value_column: Metric column name.
        zone_id: Filter to specific zone.

    Returns:
        DataFrame indexed by (hour, day_of_week) with mean and std.
    """
    data = df.copy()

    if zone_id is not None and "zone_id" in data.columns:
        data = data[data["zone_id"] == zone_id]

    if data.empty or value_column not in data.columns:
        return pd.DataFrame(columns=["hour", "day_of_week", "mean", "std"])

    if "timestamp" in data.columns:
        data["hour"] = pd.to_datetime(data["timestamp"]).dt.hour
        data["day_of_week"] = pd.to_datetime(data["timestamp"]).dt.dayofweek
    else:
        return pd.DataFrame(columns=["hour", "day_of_week", "mean", "std"])

    grouped = data.groupby(["hour", "day_of_week"])[value_column].agg(
        ["mean", "std"]
    ).reset_index()
    grouped["std"] = grouped["std"].fillna(0)

    return grouped


def deviation_score(current: float, mean: float, std: float) -> float:
    """Compute how many standard deviations a value is from the mean.

    Args:
        current: Current metric value.
        mean: Baseline mean.
        std: Baseline standard deviation.

    Returns:
        Number of standard deviations (signed). Returns 0.0 if std is 0.
    """
    if std == 0 or std < 1e-10:
        return 0.0
    return (current - mean) / std
