"""Deterministic rule evaluation for comfort and cost boundaries.

All functions are pure — no randomness, no external state.
"""

from __future__ import annotations

from core.afi.models import Constraint, Signal


# Default comfort constraints
COMFORT_CONSTRAINTS: list[Constraint] = [
    Constraint(
        metric="temperature_c",
        min_value=20.0,
        max_value=24.0,
        weight=1.0,
        label="Temperature",
    ),
    Constraint(
        metric="humidity_pct",
        min_value=40.0,
        max_value=60.0,
        weight=0.6,
        label="Humidity",
    ),
    Constraint(
        metric="co2_ppm", min_value=400.0, max_value=1000.0, weight=0.8, label="CO₂"
    ),
    Constraint(
        metric="illuminance_lux",
        min_value=300.0,
        max_value=500.0,
        weight=0.4,
        label="Light",
    ),
]

# Energy cost thresholds
ENERGY_COST_EUR_KWH = 0.15
HOURLY_WAGE_EUR = 12.0


def evaluate_comfort_boundary(
    signal: Signal, constraints: list[Constraint] | None = None
) -> float:
    """Evaluate how well a signal fits within comfort boundaries.

    Returns a score from 0.0 (completely outside) to 1.0 (perfectly within).
    Deterministic: same inputs always produce same output.
    """
    constraints = constraints or COMFORT_CONSTRAINTS
    for c in constraints:
        if c.metric == signal.metric:
            if c.min_value is not None and c.max_value is not None:
                mid = (c.min_value + c.max_value) / 2
                half_range = (c.max_value - c.min_value) / 2
                if half_range == 0:
                    return 1.0 if signal.value == mid else 0.0
                deviation = abs(signal.value - mid) / half_range
                return max(0.0, min(1.0, 1.0 - deviation)) * c.weight
    return 0.5  # Unknown metric — neutral score


def evaluate_cost_function(
    energy_kwh: float,
    occupancy: int,
    cost_per_kwh: float = ENERGY_COST_EUR_KWH,
    wage_per_hour: float = HOURLY_WAGE_EUR,
) -> dict[str, float]:
    """Compute energy and productivity cost for a zone.

    Returns dict with 'energy_cost', 'productivity_value', 'net_cost'.
    """
    energy_cost = energy_kwh * cost_per_kwh
    productivity_value = occupancy * wage_per_hour  # value generated per hour
    net_cost = energy_cost - (productivity_value * 0.01)  # simplified
    return {
        "energy_cost": round(energy_cost, 4),
        "productivity_value": round(productivity_value, 2),
        "net_cost": round(net_cost, 4),
    }


def compute_zone_health(
    signals: list[Signal], constraints: list[Constraint] | None = None
) -> float:
    """Compute a zone health score (0-100) from multiple signals.

    Deterministic weighted average of comfort boundary evaluations.
    """
    if not signals:
        return 50.0

    total_score = 0.0
    total_weight = 0.0
    constraints = constraints or COMFORT_CONSTRAINTS

    for signal in signals:
        score = evaluate_comfort_boundary(signal, constraints)
        matching_constraint = next(
            (c for c in constraints if c.metric == signal.metric), None
        )
        weight = matching_constraint.weight if matching_constraint else 0.5
        total_score += score * weight * signal.confidence
        total_weight += weight

    if total_weight == 0:
        return 50.0
    return round((total_score / total_weight) * 100, 1)
