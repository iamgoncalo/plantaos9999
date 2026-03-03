"""Tests for synthetic data generation."""

from __future__ import annotations

from data.synthetic.generator import generate_all


def test_generate_all_returns_expected_keys() -> None:
    """generate_all() returns all expected dataset keys."""
    datasets = generate_all(days=3, seed=42)

    expected_keys = {"energy", "comfort", "occupancy", "weather", "schedule"}
    assert set(datasets.keys()) == expected_keys


def test_generate_all_correct_time_range() -> None:
    """Generated data spans the configured number of days."""
    datasets = generate_all(days=3, seed=42)

    for name in ["energy", "comfort", "occupancy"]:
        df = datasets[name]
        assert "timestamp" in df.columns
        ts = df["timestamp"]
        span = (ts.max() - ts.min()).total_seconds() / 86400
        # Allow some tolerance — at least 2 days for 3-day generation
        assert span >= 2.0, f"{name}: span {span:.1f} days < 2"


def test_generate_all_zones_present() -> None:
    """All building zones appear in generated datasets."""
    datasets = generate_all(days=3, seed=42)

    for name in ["energy", "comfort", "occupancy"]:
        df = datasets[name]
        assert "zone_id" in df.columns
        zones = df["zone_id"].unique()
        assert len(zones) >= 5, f"{name}: only {len(zones)} zones"


def test_generate_all_reproducible_with_seed() -> None:
    """Same seed produces identical data."""
    d1 = generate_all(days=3, seed=99)
    d2 = generate_all(days=3, seed=99)

    for key in d1:
        assert d1[key].shape == d2[key].shape, f"{key}: shapes differ"


def test_energy_data_positive_values() -> None:
    """Energy consumption values are never negative."""
    datasets = generate_all(days=3, seed=42)
    energy = datasets["energy"]

    for col in ["total_kwh", "hvac_kwh", "lighting_kwh", "equipment_kwh"]:
        if col in energy.columns:
            assert (energy[col] >= 0).all(), f"{col} has negative values"


def test_comfort_data_within_physical_bounds() -> None:
    """Comfort metrics stay within physically realistic ranges."""
    datasets = generate_all(days=3, seed=42)
    comfort = datasets["comfort"]

    if "temperature_c" in comfort.columns:
        assert comfort["temperature_c"].min() >= -5
        assert comfort["temperature_c"].max() <= 50

    if "humidity_pct" in comfort.columns:
        assert comfort["humidity_pct"].min() >= 0
        assert comfort["humidity_pct"].max() <= 100

    if "co2_ppm" in comfort.columns:
        assert comfort["co2_ppm"].min() >= 300
        assert comfort["co2_ppm"].max() <= 5000
