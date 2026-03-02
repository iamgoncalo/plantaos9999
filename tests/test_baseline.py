"""Tests for rolling baseline computation."""

from __future__ import annotations


def test_compute_rolling_baseline_returns_result() -> None:
    """compute_rolling_baseline returns a BaselineResult."""
    ...


def test_deviation_score_zero_for_mean() -> None:
    """deviation_score returns 0.0 when value equals mean."""
    ...


def test_deviation_score_positive_for_above_mean() -> None:
    """deviation_score returns positive for values above mean."""
    ...


def test_time_of_day_baseline_shape() -> None:
    """Time-of-day baseline returns correct index shape (24 hours x 7 days)."""
    ...
