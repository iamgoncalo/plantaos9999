"""Anomaly detection using Z-score and Isolation Forest.

Detects anomalous readings in energy, comfort, and occupancy data
using both statistical (Z-score) and machine learning (Isolation Forest)
approaches. Injects 3-5 realistic anomalies per week.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel


class Anomaly(BaseModel):
    """A detected anomaly in building data."""

    zone_id: str
    metric: str
    timestamp: str
    value: float
    expected: float
    deviation: float
    severity: str  # 'info', 'warning', 'critical'
    method: str  # 'zscore', 'isolation_forest'
    description: str = ""


def detect_zscore_anomalies(
    series: pd.Series,
    threshold: float = 3.0,
) -> pd.DataFrame:
    """Detect anomalies using Z-score method.

    Args:
        series: Time-indexed series of metric values.
        threshold: Z-score threshold (default 3.0 = 99.7%).

    Returns:
        DataFrame with columns: timestamp, value, zscore, is_anomaly.
    """
    ...


def detect_isolation_forest(
    df: pd.DataFrame,
    contamination: float = 0.05,
) -> pd.DataFrame:
    """Detect anomalies using Isolation Forest.

    Args:
        df: DataFrame with numeric features.
        contamination: Expected proportion of anomalies.

    Returns:
        DataFrame with added columns: anomaly_score, is_anomaly.
    """
    ...


def get_anomalies(
    zone_id: str,
    metric: str,
    method: Literal["zscore", "isolation_forest", "both"] = "both",
) -> list[Anomaly]:
    """Get detected anomalies for a zone and metric.

    Args:
        zone_id: Zone identifier.
        metric: Metric to analyze.
        method: Detection method.

    Returns:
        List of Anomaly models.
    """
    ...


def classify_severity(score: float) -> str:
    """Classify an anomaly score into severity levels.

    Args:
        score: Anomaly score (higher = more anomalous).

    Returns:
        Severity string: 'info', 'warning', or 'critical'.
    """
    ...
