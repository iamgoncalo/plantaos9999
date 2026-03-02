"""Anomaly detection using Z-score and Isolation Forest.

Detects anomalous readings in energy, comfort, and occupancy data
using both statistical (Z-score) and machine learning (Isolation Forest)
approaches.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

from core.baseline import _METRIC_MAP, get_baseline_for_zone
from data.store import store


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
    if series.empty:
        return pd.DataFrame(columns=["value", "zscore", "is_anomaly"])

    values = series.dropna()
    if values.empty or values.std() < 1e-10:
        result = pd.DataFrame({"value": values, "zscore": 0.0, "is_anomaly": False})
        return result

    mean = values.mean()
    std = values.std()
    zscores = (values - mean) / std

    result = pd.DataFrame({
        "value": values,
        "zscore": zscores,
        "is_anomaly": np.abs(zscores) > threshold,
    })

    return result


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
    result = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) == 0 or len(df) < 10:
        result["anomaly_score"] = 0.0
        result["is_anomaly"] = False
        return result

    features = df[numeric_cols].dropna()
    if len(features) < 10:
        result["anomaly_score"] = 0.0
        result["is_anomaly"] = False
        return result

    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )

    predictions = iso_forest.fit_predict(features)
    scores = iso_forest.decision_function(features)

    # Map to result DataFrame (handle dropped NaN rows)
    result["anomaly_score"] = 0.0
    result["is_anomaly"] = False
    result.loc[features.index, "anomaly_score"] = -scores  # Higher = more anomalous
    result.loc[features.index, "is_anomaly"] = predictions == -1

    return result


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
    mapping = _METRIC_MAP.get(metric)
    if mapping is None:
        logger.warning(f"Unknown metric '{metric}' for anomaly detection")
        return []

    dataset_name, column_name = mapping

    zone_df = store.get_zone_data(dataset_name, zone_id)
    if zone_df is None or zone_df.empty:
        return []

    if column_name not in zone_df.columns:
        return []

    # Get baseline for context
    baseline = get_baseline_for_zone(zone_id, metric)
    expected = baseline.mean

    anomalies: list[Anomaly] = []

    # Z-score detection
    if method in ("zscore", "both"):
        series = zone_df[column_name]
        zscore_results = detect_zscore_anomalies(series, threshold=2.0)
        anomaly_rows = zscore_results[zscore_results["is_anomaly"]]

        for idx in anomaly_rows.index:
            ts = zone_df.loc[idx, "timestamp"] if "timestamp" in zone_df.columns else "unknown"
            val = float(anomaly_rows.loc[idx, "value"])
            zscore = float(anomaly_rows.loc[idx, "zscore"])
            severity = classify_severity(abs(zscore))

            anomalies.append(Anomaly(
                zone_id=zone_id,
                metric=metric,
                timestamp=str(ts),
                value=round(val, 2),
                expected=round(expected, 2),
                deviation=round(zscore, 2),
                severity=severity,
                method="zscore",
                description=f"{metric} at {val:.1f} is {abs(zscore):.1f}σ from baseline {expected:.1f}",
            ))

    # Isolation Forest detection
    if method in ("isolation_forest", "both"):
        numeric_cols = zone_df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols and len(zone_df) >= 10:
            iso_results = detect_isolation_forest(zone_df[numeric_cols])
            iso_anomalies = iso_results[iso_results["is_anomaly"]]

            for idx in iso_anomalies.index:
                ts = zone_df.loc[idx, "timestamp"] if "timestamp" in zone_df.columns else "unknown"
                val = float(zone_df.loc[idx, column_name]) if column_name in zone_df.columns else 0
                score = float(iso_anomalies.loc[idx, "anomaly_score"])
                severity = classify_severity(score * 3)

                # Avoid duplicates with z-score (same timestamp + zone)
                ts_str = str(ts)
                if not any(a.timestamp == ts_str and a.method == "zscore" for a in anomalies):
                    anomalies.append(Anomaly(
                        zone_id=zone_id,
                        metric=metric,
                        timestamp=ts_str,
                        value=round(val, 2),
                        expected=round(expected, 2),
                        deviation=round(score, 2),
                        severity=severity,
                        method="isolation_forest",
                        description=f"Multivariate anomaly detected (score={score:.2f})",
                    ))

    # Sort by timestamp, limit to most recent
    anomalies.sort(key=lambda a: a.timestamp, reverse=True)
    return anomalies[:100]


def classify_severity(score: float) -> str:
    """Classify an anomaly score into severity levels.

    Args:
        score: Anomaly score (higher = more anomalous).

    Returns:
        Severity string: 'info', 'warning', or 'critical'.
    """
    if score >= 3.0:
        return "critical"
    if score >= 2.0:
        return "warning"
    return "info"
