"""Tests for the AFI engine core computations."""

from __future__ import annotations


from core.afi_engine import (
    compute_distortion,
    compute_fda,
    compute_financial_bleed,
    compute_freedom,
    compute_perception,
    compute_productivity,
    decompose_freedom_change,
)


def test_perception_positive() -> None:
    """Perception P is positive for a connected zone."""
    result = compute_perception("p0_circulacao")
    assert result.P > 0
    assert result.N >= 1
    assert result.T > 0


def test_perception_uses_path_entropy() -> None:
    """Corridor with many exits has higher P than dead-end room."""
    corridor = compute_perception("p0_circulacao")
    dead_end = compute_perception("p0_auditorio")
    assert corridor.P > dead_end.P


def test_distortion_ge_one() -> None:
    """Distortion D is always >= 1 (no barrier = 1.0)."""
    result = compute_distortion("p0_hall")
    assert result.D >= 1.0


def test_distortion_increases_with_barriers() -> None:
    """Distortion increases when fire barrier is set."""
    normal = compute_distortion("p0_hall")
    with_fire = compute_distortion("p0_hall", overrides={"fire": 50.0})
    assert with_fire.D >= normal.D


def test_freedom_equals_p_over_d() -> None:
    """Freedom F = P / D within rounding tolerance."""
    result = compute_freedom("p0_hall")
    expected_f = result.P / result.D if result.D > 0 else 0.0
    assert abs(result.F - expected_f) < 0.01


def test_freedom_decreases_with_barriers() -> None:
    """Freedom drops when distortion barriers are added."""
    normal = compute_freedom("p0_hall")
    stressed = compute_freedom("p0_hall", distortion_overrides={"fire": 100.0})
    assert stressed.F <= normal.F


def test_financial_bleed_nonnegative() -> None:
    """Financial bleed is always non-negative."""
    bleed = compute_financial_bleed("p0_hall")
    assert bleed.total_bleed_eur_hr >= 0.0
    assert bleed.energy_cost_eur_hr >= 0.0


def test_financial_bleed_capped() -> None:
    """Financial bleed per zone is capped at MAX_ZONE_BLEED_EUR_HR."""
    from core.afi_engine import MAX_ZONE_BLEED_EUR_HR

    bleed = compute_financial_bleed("p0_hall")
    assert bleed.total_bleed_eur_hr <= MAX_ZONE_BLEED_EUR_HR


def test_fda_returns_zero_initially() -> None:
    """FDA returns 0 when there's no history (or only one value)."""
    fda = compute_fda("test_zone_fda", 5.0)
    assert fda == 0.0


def test_fda_detects_drop() -> None:
    """FDA detects a significant freedom drop after building history."""
    from core.afi_engine import _freedom_history

    # Build up a stable history
    zone = "test_zone_fda_drop"
    _freedom_history[zone] = [5.0] * 50

    # Inject a sharp drop
    fda = compute_fda(zone, 1.0, tau=2.0)
    # With mean=5.0 and std~0, any drop should give high FDA
    assert fda > 0


def test_decompose_freedom_change_stable() -> None:
    """Decomposition returns 'Freedom stable' when nothing changes."""
    result = decompose_freedom_change(
        prev_P=3.0,
        prev_D=1.5,
        curr_P=3.0,
        curr_D=1.5,
        curr_barriers={"temperature": 1.0},
    )
    assert result["explanation"] == "Freedom stable"
    assert abs(result["delta_P_pct"]) < 1.0
    assert abs(result["delta_D_pct"]) < 1.0


def test_decompose_freedom_change_detects_distortion_increase() -> None:
    """Decomposition detects a distortion increase."""
    result = decompose_freedom_change(
        prev_P=3.0,
        prev_D=1.5,
        curr_P=3.0,
        curr_D=3.0,
        curr_barriers={"temperature": 5.0},
    )
    assert result["delta_D_pct"] > 0
    assert "Distortion increased" in result["explanation"]
    assert result["dominant_barrier"] == "temperature"


def test_productivity_zero_people() -> None:
    """Productivity is 0 when no people are present."""
    assert compute_productivity(80.0, 0) == 0.0


def test_productivity_positive() -> None:
    """Productivity is positive with people and comfort."""
    prod = compute_productivity(80.0, 10, disruption_count=0)
    assert prod > 0


def test_productivity_decreases_with_disruptions() -> None:
    """Disruptions reduce productivity."""
    no_disruption = compute_productivity(80.0, 10, disruption_count=0)
    with_disruption = compute_productivity(80.0, 10, disruption_count=5)
    assert with_disruption < no_disruption


def test_productivity_never_negative() -> None:
    """Productivity is clamped to 0 (never negative)."""
    prod = compute_productivity(10.0, 1, disruption_count=100)
    assert prod >= 0.0
