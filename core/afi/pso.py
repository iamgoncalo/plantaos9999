"""Particle Swarm Optimization for HVAC setpoint optimization.

Finds optimal (temperature_setpoint, ventilation_rate) per zone
that minimizes energy cost while satisfying comfort constraints.
Uses standard PSO with inertia weight and cognitive/social components.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from pydantic import BaseModel, Field

from config.thresholds import COMFORT_BANDS


class PSOConfig(BaseModel):
    """PSO hyperparameters."""

    n_particles: int = 30
    max_iter: int = 50
    omega: float = 0.7  # inertia weight
    c1: float = 1.5  # cognitive component
    c2: float = 1.5  # social component
    seed: int = 42


class PSOResult(BaseModel):
    """Result of PSO optimization."""

    best_position: list[float] = Field(default_factory=list)
    best_fitness: float = 0.0
    iterations_run: int = 0
    converged: bool = False


# Convergence threshold: stop when global best improves less than this
_CONVERGENCE_TOL: float = 1e-6
_CONVERGENCE_WINDOW: int = 5


def pso_optimize(
    objective_fn: Callable[[list[float]], float],
    bounds: list[tuple[float, float]],
    config: PSOConfig | None = None,
) -> PSOResult:
    """Run PSO to minimize an objective function.

    Standard PSO velocity update:
        v = omega * v + c1 * r1 * (pbest - x) + c2 * r2 * (gbest - x)
        x = x + v

    Velocity is clamped to 20% of the search range per dimension to
    prevent particles from flying out of bounds excessively.

    Args:
        objective_fn: Function taking position vector, returning fitness
            (lower is better).
        bounds: List of (min, max) tuples per dimension.
        config: PSO hyperparameters.

    Returns:
        PSOResult with best position and fitness.
    """
    cfg = config or PSOConfig()
    rng = np.random.default_rng(cfg.seed)

    n_dim = len(bounds)
    lower = np.array([b[0] for b in bounds])
    upper = np.array([b[1] for b in bounds])
    ranges = upper - lower

    # Velocity clamp: 20% of range per dimension
    v_max = 0.2 * ranges

    # Initialize particle positions uniformly within bounds
    positions = rng.uniform(lower, upper, size=(cfg.n_particles, n_dim))
    velocities = rng.uniform(-v_max, v_max, size=(cfg.n_particles, n_dim))

    # Evaluate initial fitness for all particles
    fitness = np.array(
        [objective_fn(positions[i].tolist()) for i in range(cfg.n_particles)]
    )

    # Personal bests
    pbest_pos = positions.copy()
    pbest_fit = fitness.copy()

    # Global best
    gbest_idx = int(np.argmin(pbest_fit))
    gbest_pos = pbest_pos[gbest_idx].copy()
    gbest_fit = float(pbest_fit[gbest_idx])

    # Track recent improvements for convergence detection
    recent_gbest: list[float] = [gbest_fit]

    iterations_run = 0
    converged = False

    for iteration in range(cfg.max_iter):
        iterations_run = iteration + 1

        # Random coefficients (vectorized across particles and dimensions)
        r1 = rng.uniform(0.0, 1.0, size=(cfg.n_particles, n_dim))
        r2 = rng.uniform(0.0, 1.0, size=(cfg.n_particles, n_dim))

        # Velocity update
        cognitive = cfg.c1 * r1 * (pbest_pos - positions)
        social = cfg.c2 * r2 * (gbest_pos - positions)
        velocities = cfg.omega * velocities + cognitive + social

        # Clamp velocity
        velocities = np.clip(velocities, -v_max, v_max)

        # Position update
        positions = positions + velocities

        # Enforce bounds by reflecting particles back inside
        below = positions < lower
        above = positions > upper
        positions = np.where(below, lower + (lower - positions) * 0.1, positions)
        positions = np.where(above, upper - (positions - upper) * 0.1, positions)
        positions = np.clip(positions, lower, upper)

        # Evaluate fitness
        fitness = np.array(
            [objective_fn(positions[i].tolist()) for i in range(cfg.n_particles)]
        )

        # Update personal bests
        improved = fitness < pbest_fit
        pbest_pos[improved] = positions[improved]
        pbest_fit[improved] = fitness[improved]

        # Update global best
        current_best_idx = int(np.argmin(pbest_fit))
        if pbest_fit[current_best_idx] < gbest_fit:
            gbest_pos = pbest_pos[current_best_idx].copy()
            gbest_fit = float(pbest_fit[current_best_idx])

        # Convergence check
        recent_gbest.append(gbest_fit)
        if len(recent_gbest) > _CONVERGENCE_WINDOW:
            recent_gbest.pop(0)
            improvement = abs(recent_gbest[0] - recent_gbest[-1])
            if improvement < _CONVERGENCE_TOL:
                converged = True
                break

    return PSOResult(
        best_position=gbest_pos.tolist(),
        best_fitness=gbest_fit,
        iterations_run=iterations_run,
        converged=converged,
    )


# ── HVAC Objective Weights ──────────────────────────────
_LAMBDA_COMFORT: float = 1.0
_LAMBDA_ENERGY: float = 0.6
_LAMBDA_CO2: float = 0.8

# HVAC bounds: [temp_setpoint_c, ventilation_ach]
_HVAC_BOUNDS: list[tuple[float, float]] = [
    (18.0, 26.0),  # temperature setpoint in Celsius
    (0.5, 5.0),  # ventilation rate in ACH
]


def _hvac_objective(
    position: list[float],
    current_temp: float,
    current_co2: float,
    current_humidity: float,
    occupant_count: int,
    outdoor_temp: float,
) -> float:
    """Compute HVAC cost for a candidate (temp_setpoint, ventilation_ach).

    Objective minimizes a weighted sum of:
      - Comfort deviation from optimal temperature band
      - Energy cost proportional to |setpoint - outdoor| and ventilation
      - CO2 penalty when ventilation is insufficient for occupancy

    Args:
        position: [temp_setpoint_c, ventilation_ach].
        current_temp: Current zone temperature in Celsius.
        current_co2: Current CO2 level in ppm.
        current_humidity: Current humidity percentage.
        occupant_count: Number of occupants in the zone.
        outdoor_temp: Outdoor temperature in Celsius.

    Returns:
        Scalar cost value (lower is better).
    """
    temp_setpoint = position[0]
    ventilation_ach = position[1]

    temp_band = COMFORT_BANDS["temperature"]
    optimal_mid = (temp_band.min_optimal + temp_band.max_optimal) / 2.0
    optimal_half = (temp_band.max_optimal - temp_band.min_optimal) / 2.0

    # Comfort cost: deviation of setpoint from optimal center
    temp_deviation = abs(temp_setpoint - optimal_mid) / max(optimal_half, 0.1)
    comfort_cost = temp_deviation**2

    # Humidity penalty if temperature setpoint is extreme
    humidity_band = COMFORT_BANDS["humidity"]
    if current_humidity < humidity_band.min_optimal:
        comfort_cost += 0.3 * ((humidity_band.min_optimal - current_humidity) / 20.0)
    elif current_humidity > humidity_band.max_optimal:
        comfort_cost += 0.3 * ((current_humidity - humidity_band.max_optimal) / 20.0)

    # Energy cost: proportional to thermal gap and ventilation effort
    thermal_gap = abs(temp_setpoint - outdoor_temp)
    energy_cost = 0.05 * thermal_gap**1.5 + 0.3 * ventilation_ach**1.2

    # CO2 penalty: estimate steady-state CO2 from occupancy vs ventilation
    # Each person emits ~0.005 L/s CO2; ventilation dilutes proportionally
    co2_generation = occupant_count * 40.0  # ppm contribution per person
    effective_dilution = max(ventilation_ach, 0.1)
    projected_co2 = 400.0 + co2_generation / effective_dilution

    co2_band = COMFORT_BANDS["co2"]
    co2_cost = 0.0
    if projected_co2 > co2_band.max_optimal:
        co2_excess = (projected_co2 - co2_band.max_optimal) / 200.0
        co2_cost = co2_excess**2

    total = (
        _LAMBDA_COMFORT * comfort_cost
        + _LAMBDA_ENERGY * energy_cost
        + _LAMBDA_CO2 * co2_cost
    )
    return float(total)


def optimize_hvac_setpoints(
    zone_states: dict[str, dict],
    weather: dict | None = None,
    config: PSOConfig | None = None,
) -> dict[str, dict[str, float]]:
    """Find optimal HVAC setpoints for each zone using PSO.

    Objective per zone: J = lambda_C * Comfort + lambda_E * Energy
                          + lambda_CO2 * CO2Penalty

    Each zone optimizes two variables:
        [temp_setpoint (18-26 C), ventilation_rate (0.5-5.0 ACH)]

    Args:
        zone_states: Dict of zone_id -> {temperature_c, co2_ppm,
            humidity_pct, occupant_count, energy_kwh}.
        weather: Optional dict with outdoor_temp_c, outdoor_humidity_pct.
        config: PSO config override.

    Returns:
        Dict of zone_id -> {temp_setpoint_c, ventilation_ach,
            projected_comfort, projected_energy_kwh, improvement_pct}.
    """
    outdoor_temp = 13.0  # Default for March in Aveiro
    if weather is not None:
        outdoor_temp = weather.get("outdoor_temp_c", outdoor_temp)

    results: dict[str, dict[str, float]] = {}

    for zone_id, state in zone_states.items():
        current_temp = float(state.get("temperature_c", 22.0))
        current_co2 = float(state.get("co2_ppm", 500.0))
        current_humidity = float(state.get("humidity_pct", 50.0))
        occupant_count = int(state.get("occupant_count", 0))

        # Compute baseline cost with current conditions as reference
        baseline_setpoint = [current_temp, 2.0]  # assume 2 ACH baseline
        baseline_cost = _hvac_objective(
            baseline_setpoint,
            current_temp,
            current_co2,
            current_humidity,
            occupant_count,
            outdoor_temp,
        )

        # Define zone-specific objective closure
        def zone_objective(
            pos: list[float],
            _ct: float = current_temp,
            _co2: float = current_co2,
            _hum: float = current_humidity,
            _occ: int = occupant_count,
            _ot: float = outdoor_temp,
        ) -> float:
            return _hvac_objective(pos, _ct, _co2, _hum, _occ, _ot)

        result = pso_optimize(zone_objective, _HVAC_BOUNDS, config)

        opt_temp = result.best_position[0]
        opt_vent = result.best_position[1]

        # Compute projected comfort score (0-100)
        temp_band = COMFORT_BANDS["temperature"]
        opt_mid = (temp_band.min_optimal + temp_band.max_optimal) / 2.0
        opt_half = (temp_band.max_optimal - temp_band.min_optimal) / 2.0
        temp_score = max(0.0, 1.0 - abs(opt_temp - opt_mid) / max(opt_half, 0.1))
        projected_comfort = round(temp_score * 100.0, 1)

        # Projected energy: simplified model based on thermal gap + vent
        thermal_gap = abs(opt_temp - outdoor_temp)
        projected_energy = round(0.1 * thermal_gap + 0.2 * opt_vent, 2)

        # Improvement percentage relative to baseline
        improvement_pct = 0.0
        if baseline_cost > 0:
            improvement_pct = round(
                (1.0 - result.best_fitness / baseline_cost) * 100.0, 1
            )

        results[zone_id] = {
            "temp_setpoint_c": round(opt_temp, 1),
            "ventilation_ach": round(opt_vent, 2),
            "projected_comfort": projected_comfort,
            "projected_energy_kwh": projected_energy,
            "improvement_pct": max(0.0, improvement_pct),
        }

    return results
