"""Tests for anomaly detection."""

from __future__ import annotations


def test_zscore_detects_outliers() -> None:
    """Z-score method flags values beyond threshold."""
    ...


def test_isolation_forest_detects_injected_anomalies() -> None:
    """Isolation forest flags injected anomalous data points."""
    ...


def test_classify_severity_levels() -> None:
    """classify_severity returns correct severity strings."""
    ...


def test_get_anomalies_returns_anomaly_models() -> None:
    """get_anomalies returns list of Anomaly pydantic models."""
    ...
