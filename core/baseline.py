"""Rolling statistical baselines.

Computes rolling mean, standard deviation, and percentile baselines
for all metrics, enabling deviation detection and trend analysis.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel


class BaselineResult(BaseModel):
    """Result of a baseline computation for a metric."""

    zone_id: str
    metric: str
    mean: float
    std: float
    p25: float
    p75: float
    window_days: int


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
    ...


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
    ...


def compute_time_of_day_baseline(
    df: pd.DataFrame,
    value_column: str,
    zone_id: str | None = None,
) -> pd.DataFrame:
    """Compute typical values by time-of-day and day-of-week.

    Args:
        df: Input DataFrame with timestamp index.
        value_column: Metric column name.
        zone_id: Filter to specific zone.

    Returns:
        DataFrame indexed by (hour, day_of_week) with mean and std.
    """
    ...


def deviation_score(current: float, mean: float, std: float) -> float:
    """Compute how many standard deviations a value is from the mean.

    Args:
        current: Current metric value.
        mean: Baseline mean.
        std: Baseline standard deviation.

    Returns:
        Number of standard deviations (signed). Returns 0.0 if std is 0.
    """
    ...
