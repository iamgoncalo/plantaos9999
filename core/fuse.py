"""Stream fusion — 1D Kalman filter per zone/metric + Bayesian occupancy.

Replaces the simple EMA with a proper Kalman filter that adapts its
measurement noise R_i based on sensor health (battery, staleness, drift).
Outlier events are still silently skipped. Also provides a logit-space
Bayesian fusion function for multi-sensor occupancy estimation.
"""

from __future__ import annotations

import math
from collections import defaultdict

from pydantic import BaseModel, Field

from core.validate import ValidatedEvent


# ═══════════════════════════════════════════════
# Kalman Filter State
# ═══════════════════════════════════════════════


class KalmanState(BaseModel):
    """State for a 1D Kalman filter tracking a single metric."""

    x_hat: float = Field(description="State estimate")
    P: float = Field(default=1.0, description="Estimate error covariance")
    Q: float = Field(default=0.1, description="Process noise covariance")
    R: float = Field(default=0.5, description="Measurement noise covariance")


def kalman_predict(state: KalmanState) -> KalmanState:
    """Prediction step: propagate state forward one timestep.

    x̂_k|k-1 = x̂_{k-1} (static model)
    P_k|k-1 = P_{k-1} + Q

    Args:
        state: Current Kalman state.

    Returns:
        Predicted state (x_hat unchanged, P increased by Q).
    """
    return KalmanState(
        x_hat=state.x_hat,
        P=state.P + state.Q,
        Q=state.Q,
        R=state.R,
    )


def kalman_update(
    state: KalmanState,
    measurement: float,
    R_override: float | None = None,
) -> KalmanState:
    """Update step: incorporate a new measurement.

    K = P / (P + R)
    x̂ = x̂ + K × (z - x̂)
    P = (1 - K) × P

    Args:
        state: Predicted Kalman state.
        measurement: New sensor measurement z.
        R_override: Override measurement noise (e.g. for degraded sensors).

    Returns:
        Updated state with new estimate and reduced uncertainty.
    """
    R = R_override if R_override is not None else state.R
    R = max(R, 0.001)  # prevent division by zero
    P = state.P

    K = P / (P + R)
    x_hat = state.x_hat + K * (measurement - state.x_hat)
    P_new = (1.0 - K) * P

    return KalmanState(x_hat=x_hat, P=P_new, Q=state.Q, R=state.R)


def compute_adaptive_R(
    base_R: float,
    battery_pct: float = 100.0,
    stale_minutes: float = 0.0,
    drift_detected: bool = False,
) -> float:
    """Compute adaptive measurement noise based on sensor health.

    R increases when:
    - Battery below 20%: R × 2
    - Sensor stale (>10 min): R × (1 + stale_minutes/10)
    - Drift detected: R × 3

    Args:
        base_R: Baseline measurement noise.
        battery_pct: Sensor battery percentage (0-100).
        stale_minutes: Minutes since last valid reading.
        drift_detected: Whether sensor drift has been flagged.

    Returns:
        Adjusted measurement noise R_i.
    """
    R = base_R
    if battery_pct < 20.0:
        R *= 2.0
    if stale_minutes > 10.0:
        R *= 1.0 + stale_minutes / 10.0
    if drift_detected:
        R *= 3.0
    return R


# ═══════════════════════════════════════════════
# Module State
# ═══════════════════════════════════════════════

# Kalman filter per (zone_id, metric)
_ZONE_KALMAN: dict[str, dict[str, KalmanState]] = defaultdict(dict)

# Default process/measurement noise by metric type
_METRIC_DEFAULTS: dict[str, tuple[float, float]] = {
    # metric: (Q_process, R_measurement)
    "temperature_c": (0.05, 0.3),
    "humidity_pct": (0.1, 1.0),
    "co2_ppm": (5.0, 20.0),
    "illuminance_lux": (2.0, 10.0),
    "occupancy_count": (0.5, 2.0),
    "total_kwh": (0.01, 0.1),
}


def fuse_event(
    event: ValidatedEvent,
    sensor_health: dict | None = None,
) -> dict[str, float]:
    """Incorporate a validated event into the fused zone state via Kalman.

    Outliers are ignored. Each metric maintains its own 1D Kalman filter.
    Sensor health information adjusts measurement noise R_i.

    Args:
        event: A ValidatedEvent (outlier flag checked).
        sensor_health: Optional dict with battery_pct, stale_minutes,
                       drift_detected keys.

    Returns:
        Current fused metric dict for the event's zone.
    """
    if event.is_outlier:
        return {m: s.x_hat for m, s in _ZONE_KALMAN.get(event.zone_id, {}).items()}

    zone_id = event.zone_id
    metric = event.metric
    value = event.value

    defaults = _METRIC_DEFAULTS.get(metric, (0.1, 0.5))
    Q_default, R_default = defaults

    # Get or create Kalman state
    if metric not in _ZONE_KALMAN[zone_id]:
        _ZONE_KALMAN[zone_id][metric] = KalmanState(
            x_hat=value,
            P=1.0,
            Q=Q_default,
            R=R_default,
        )
        return {m: s.x_hat for m, s in _ZONE_KALMAN[zone_id].items()}

    state = _ZONE_KALMAN[zone_id][metric]

    # Prediction step
    state = kalman_predict(state)

    # Compute adaptive R based on sensor health
    R_adaptive = state.R
    if sensor_health:
        R_adaptive = compute_adaptive_R(
            base_R=state.R,
            battery_pct=sensor_health.get("battery_pct", 100.0),
            stale_minutes=sensor_health.get("stale_minutes", 0.0),
            drift_detected=sensor_health.get("drift_detected", False),
        )

    # Update step
    state = kalman_update(state, value, R_override=R_adaptive)
    _ZONE_KALMAN[zone_id][metric] = state

    return {m: s.x_hat for m, s in _ZONE_KALMAN[zone_id].items()}


def fuse_batch(
    events: list[ValidatedEvent],
) -> dict[str, dict[str, float]]:
    """Fuse a batch of validated events and return all zones touched.

    Args:
        events: List of ValidatedEvent objects.

    Returns:
        Dict mapping zone_id to its current fused state.
    """
    touched: set[str] = set()
    for event in events:
        fuse_event(event)
        touched.add(event.zone_id)
    return {zid: {m: s.x_hat for m, s in _ZONE_KALMAN[zid].items()} for zid in touched}


def get_fused_state(zone_id: str) -> dict[str, float]:
    """Retrieve the current Kalman-fused state for a zone.

    Args:
        zone_id: Building zone identifier.

    Returns:
        Dict of metric_name -> estimated value (empty if unseen).
    """
    return {m: s.x_hat for m, s in _ZONE_KALMAN.get(zone_id, {}).items()}


def get_kalman_diagnostics(zone_id: str) -> dict[str, dict]:
    """Retrieve Kalman filter diagnostics for edge fusion panel.

    Args:
        zone_id: Building zone identifier.

    Returns:
        Dict of metric_name -> {x_hat, P, Q, R} state values.
    """
    return {m: s.model_dump() for m, s in _ZONE_KALMAN.get(zone_id, {}).items()}


def reset_fused_state() -> None:
    """Clear all fused state (e.g. on data regeneration)."""
    _ZONE_KALMAN.clear()


def set_alpha(alpha: float) -> None:
    """Update process noise scaling (compatibility shim).

    Maps alpha to Q scaling: higher alpha = more responsive = higher Q.

    Args:
        alpha: Value in (0, 1]. Higher = more responsive.
    """
    alpha = max(0.01, min(1.0, alpha))
    scale = alpha / 0.3  # normalize to default alpha=0.3
    for metric, (Q_base, R_base) in _METRIC_DEFAULTS.items():
        _METRIC_DEFAULTS[metric] = (Q_base * scale, R_base)


# ═══════════════════════════════════════════════
# Bayesian Occupancy Fusion
# ═══════════════════════════════════════════════


def fuse_occupancy_bayesian(
    detector_probs: dict[str, float],
    weights: dict[str, float] | None = None,
    occ_max: int = 50,
) -> int:
    """Bayesian fusion of occupancy evidence from multiple detectors.

    Uses weighted logit-space linear combination:
        logit(p_occ) = Σ w_i × logit(p_i)
        p_occ = sigmoid(logit(p_occ))
        occ_count = round(p_occ × occ_max)

    Args:
        detector_probs: Dict of detector_name -> detection probability [0,1].
            E.g. {"pir": 0.8, "mmwave": 0.7, "booking": 0.5}
        weights: Optional dict of detector_name -> weight.
            Defaults to equal weights.
        occ_max: Maximum occupancy capacity of the zone.

    Returns:
        Estimated occupancy count (integer).
    """
    if not detector_probs:
        return 0

    default_weights: dict[str, float] = {
        "pir": 0.8,
        "mmwave": 1.2,
        "booking": 0.5,
        "camera_count": 1.5,
        "co2_derived": 0.6,
        "door_contact": 0.3,
    }
    w = weights or default_weights

    logit_sum = 0.0
    weight_sum = 0.0

    for detector, prob in detector_probs.items():
        # Clamp to avoid log(0)
        p = max(0.01, min(0.99, prob))
        wi = w.get(detector, 1.0)
        logit_sum += wi * math.log(p / (1.0 - p))
        weight_sum += wi

    if weight_sum == 0:
        return 0

    # Normalize by total weight for stability
    logit_avg = logit_sum / weight_sum
    # Clamp to avoid overflow in exp
    logit_avg = max(-10.0, min(10.0, logit_avg))
    p_occ = 1.0 / (1.0 + math.exp(-logit_avg))

    return round(p_occ * occ_max)
