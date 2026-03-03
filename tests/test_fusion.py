"""Tests for the Kalman filter fusion module."""

from __future__ import annotations


from core.fuse import (
    KalmanState,
    compute_adaptive_R,
    fuse_occupancy_bayesian,
    kalman_predict,
    kalman_update,
    reset_fused_state,
)


def test_kalman_predict_increases_uncertainty() -> None:
    """Prediction step increases P by Q."""
    state = KalmanState(x_hat=20.0, P=1.0, Q=0.1, R=0.5)
    predicted = kalman_predict(state)
    assert predicted.P == state.P + state.Q
    assert predicted.x_hat == state.x_hat


def test_kalman_update_reduces_uncertainty() -> None:
    """Update step reduces P (gains information)."""
    state = KalmanState(x_hat=20.0, P=2.0, Q=0.1, R=0.5)
    updated = kalman_update(state, measurement=21.0)
    assert updated.P < state.P


def test_kalman_converges_to_true_value() -> None:
    """Repeated measurements converge the estimate to the true value."""
    true_value = 25.0
    state = KalmanState(x_hat=0.0, P=100.0, Q=0.01, R=1.0)

    for _ in range(50):
        state = kalman_predict(state)
        state = kalman_update(state, measurement=true_value)

    assert abs(state.x_hat - true_value) < 0.5


def test_kalman_update_with_R_override() -> None:
    """R override changes how much the filter trusts the measurement."""
    state = KalmanState(x_hat=20.0, P=1.0, Q=0.1, R=0.5)
    predicted = kalman_predict(state)

    # Low R: trust the measurement more
    low_R = kalman_update(predicted, 25.0, R_override=0.01)
    # High R: trust the measurement less
    high_R = kalman_update(predicted, 25.0, R_override=100.0)

    # Low R should move x_hat closer to 25.0
    assert abs(low_R.x_hat - 25.0) < abs(high_R.x_hat - 25.0)


def test_adaptive_R_increases_for_low_battery() -> None:
    """Adaptive R is higher when battery is low."""
    base_R = 0.5
    normal = compute_adaptive_R(base_R, battery_pct=80.0)
    low_batt = compute_adaptive_R(base_R, battery_pct=10.0)
    assert low_batt > normal


def test_adaptive_R_increases_for_stale_sensor() -> None:
    """Adaptive R is higher when sensor data is stale."""
    base_R = 0.5
    fresh = compute_adaptive_R(base_R, stale_minutes=0.0)
    stale = compute_adaptive_R(base_R, stale_minutes=30.0)
    assert stale > fresh


def test_adaptive_R_increases_for_drift() -> None:
    """Adaptive R is higher when drift is detected."""
    base_R = 0.5
    no_drift = compute_adaptive_R(base_R, drift_detected=False)
    with_drift = compute_adaptive_R(base_R, drift_detected=True)
    assert with_drift > no_drift


def test_bayesian_occupancy_empty() -> None:
    """Empty detector probs return 0."""
    assert fuse_occupancy_bayesian({}) == 0


def test_bayesian_occupancy_high_prob() -> None:
    """High detection probabilities yield near-max occupancy."""
    occ = fuse_occupancy_bayesian(
        {"pir": 0.95, "mmwave": 0.95, "camera_count": 0.95},
        occ_max=50,
    )
    assert occ >= 40, f"Expected >=40, got {occ}"


def test_bayesian_occupancy_low_prob() -> None:
    """Low detection probabilities yield near-zero occupancy."""
    occ = fuse_occupancy_bayesian(
        {"pir": 0.05, "mmwave": 0.05},
        occ_max=50,
    )
    assert occ <= 10, f"Expected <=10, got {occ}"


def test_bayesian_occupancy_mixed_signals() -> None:
    """Mixed signals from detectors produce an intermediate result."""
    occ = fuse_occupancy_bayesian(
        {"pir": 0.9, "mmwave": 0.1},
        occ_max=50,
    )
    assert 5 <= occ <= 45


def test_reset_fused_state() -> None:
    """reset_fused_state clears all Kalman state."""
    from core.fuse import _ZONE_KALMAN, fuse_event
    from core.validate import ValidatedEvent

    # Prime some state
    event = ValidatedEvent(
        sensor_id="test_sensor_01",
        zone_id="test_reset_zone",
        metric="temperature_c",
        value=21.0,
        is_outlier=False,
    )
    fuse_event(event)
    assert "test_reset_zone" in _ZONE_KALMAN

    reset_fused_state()
    assert len(_ZONE_KALMAN) == 0
