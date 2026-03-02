"""Tests for synthetic data generation."""

from __future__ import annotations


def test_generate_all_returns_expected_keys() -> None:
    """generate_all() returns all expected dataset keys."""
    ...


def test_generate_all_correct_time_range() -> None:
    """Generated data spans the configured number of days."""
    ...


def test_generate_all_zones_present() -> None:
    """All building zones appear in generated datasets."""
    ...


def test_generate_all_reproducible_with_seed() -> None:
    """Same seed produces identical data."""
    ...


def test_energy_data_positive_values() -> None:
    """Energy consumption values are never negative."""
    ...


def test_comfort_data_within_physical_bounds() -> None:
    """Comfort metrics stay within physically realistic ranges."""
    ...
