"""Tests for rolling baseline computation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.baseline import BaselineResult, compute_rolling_baseline, deviation_score


def test_compute_rolling_baseline_returns_result() -> None:
    """compute_rolling_baseline returns a BaselineResult."""
    rng = np.random.default_rng(42)
    series = pd.Series(rng.normal(21.0, 1.5, size=500))

    result = compute_rolling_baseline(series, window=7)

    assert isinstance(result, BaselineResult)
    assert result.window_days == 7
    assert abs(result.mean - 21.0) < 1.0
    assert result.std > 0
    assert result.p25 < result.p50 < result.p75


def test_compute_rolling_baseline_empty() -> None:
    """Empty series returns zero baseline."""
    result = compute_rolling_baseline(pd.Series(dtype=float))
    assert result.mean == 0
    assert result.std == 0


def test_deviation_score_zero_for_mean() -> None:
    """deviation_score returns 0.0 when value equals mean."""
    score = deviation_score(current=20.0, mean=20.0, std=2.0)
    assert score == 0.0


def test_deviation_score_positive_for_above_mean() -> None:
    """deviation_score returns positive for values above mean."""
    score = deviation_score(current=25.0, mean=20.0, std=2.0)
    assert score == 2.5


def test_deviation_score_negative_for_below_mean() -> None:
    """deviation_score returns negative for values below mean."""
    score = deviation_score(current=15.0, mean=20.0, std=2.0)
    assert score == -2.5


def test_deviation_score_zero_std() -> None:
    """deviation_score returns 0.0 when std is 0."""
    score = deviation_score(current=25.0, mean=20.0, std=0.0)
    assert score == 0.0


def test_time_of_day_baseline_shape() -> None:
    """Time-of-day baseline returns correct grouped shape."""
    from core.baseline import compute_time_of_day_baseline

    rng = np.random.default_rng(42)
    n = 7 * 24 * 4  # 7 days, 15-min intervals
    timestamps = pd.date_range("2026-02-01", periods=n, freq="15min")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "zone_id": "p0_hall",
            "temperature_c": rng.normal(21.0, 1.0, size=n),
        }
    )

    result = compute_time_of_day_baseline(df, "temperature_c")

    assert "hour" in result.columns
    assert "day_of_week" in result.columns
    assert "mean" in result.columns
    # Should have entries for hours × days that exist in data
    assert len(result) > 0
    assert result["hour"].max() <= 23
    assert result["day_of_week"].max() <= 6
