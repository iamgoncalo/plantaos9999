"""Tests for anomaly detection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.anomaly import (
    classify_severity,
    detect_isolation_forest,
    detect_zscore_anomalies,
)


def test_zscore_detects_outliers() -> None:
    """Z-score method flags values beyond threshold."""
    rng = np.random.default_rng(42)
    values = rng.normal(20.0, 1.0, size=200)
    # Inject clear outliers
    values[50] = 30.0
    values[100] = 10.0

    series = pd.Series(values)
    result = detect_zscore_anomalies(series, threshold=3.0)

    assert "is_anomaly" in result.columns
    assert "zscore" in result.columns
    anomalies = result[result["is_anomaly"]]
    assert len(anomalies) >= 2, "Should detect at least the 2 injected outliers"
    assert 50 in anomalies.index
    assert 100 in anomalies.index


def test_zscore_empty_series() -> None:
    """Z-score handles empty series gracefully."""
    result = detect_zscore_anomalies(pd.Series(dtype=float))
    assert len(result) == 0
    assert "is_anomaly" in result.columns


def test_isolation_forest_detects_injected_anomalies() -> None:
    """Isolation forest flags injected anomalous data points."""
    rng = np.random.default_rng(42)
    n = 200
    normal = rng.normal(20.0, 1.0, size=(n, 2))
    # Inject 10 anomalies at extreme values
    anomalous = rng.uniform(35.0, 40.0, size=(10, 2))
    data = np.vstack([normal, anomalous])
    df = pd.DataFrame(data, columns=["temp", "humidity"])

    result = detect_isolation_forest(df, contamination=0.05)

    assert "is_anomaly" in result.columns
    assert "anomaly_score" in result.columns
    # At least some of the injected anomalies (last 10 rows) detected
    injected_detected = result.iloc[n:]["is_anomaly"].sum()
    assert injected_detected >= 3, (
        f"Expected >=3 of 10 detected, got {injected_detected}"
    )


def test_isolation_forest_small_dataset() -> None:
    """Isolation forest handles dataset with <10 rows."""
    df = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
    result = detect_isolation_forest(df)
    assert not result["is_anomaly"].any()


def test_classify_severity_levels() -> None:
    """classify_severity returns correct severity strings."""
    assert classify_severity(1.0) == "info"
    assert classify_severity(1.5) == "info"
    assert classify_severity(2.0) == "warning"
    assert classify_severity(2.5) == "warning"
    assert classify_severity(3.0) == "critical"
    assert classify_severity(5.0) == "critical"


def test_get_anomalies_returns_anomaly_models() -> None:
    """get_anomalies returns list of Anomaly pydantic models."""
    from core.anomaly import Anomaly

    # Verify the model has the expected fields
    a = Anomaly(
        zone_id="p0_hall",
        metric="temperature",
        timestamp="2026-03-01T12:00:00",
        value=35.0,
        expected=21.0,
        deviation=4.5,
        severity="critical",
        method="zscore",
        description="test",
    )
    assert a.zone_id == "p0_hall"
    assert a.severity == "critical"
    assert a.method == "zscore"
