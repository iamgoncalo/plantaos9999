"""True physics simulation engine for PlantaOS Digital Twin.

Uses scipy.integrate.odeint for temperature and CO2 drift modelling
based on real thermodynamics (Newton's law of cooling, CO2 mass balance).
Provides EMA smoothing for financial metrics and edge-fusion blending
for mixing simulated data with sensor readings.
"""

from __future__ import annotations

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field
from scipy.integrate import odeint

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_zone_by_id
from data.store import store


# ═══════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════


class RoomPhysicsState(BaseModel):
    """Instantaneous physical state of a single room/zone."""

    zone_id: str = Field(description="Unique zone identifier")
    temperature_c: float = Field(default=22.0, description="Indoor temperature (C)")
    co2_ppm: float = Field(default=420.0, description="Indoor CO2 concentration (ppm)")
    humidity_pct: float = Field(default=50.0, description="Relative humidity (%)")
    occupant_count: int = Field(default=0, description="Current number of occupants")
    hvac_power_w: float = Field(default=0.0, description="HVAC heat input/removal (W)")
    ventilation_ach: float = Field(
        default=2.0, description="Ventilation rate (air changes per hour)"
    )


class PhysicsSimConfig(BaseModel):
    """Tunable constants for the physics simulation engine."""

    outdoor_temp_c: float = Field(default=12.0, description="Outdoor temperature (C)")
    outdoor_co2_ppm: float = Field(default=420.0, description="Outdoor CO2 (ppm)")
    ceiling_height_m: float = Field(default=3.2, description="Room ceiling height (m)")
    air_density: float = Field(default=1.225, description="Air density (kg/m3)")
    air_specific_heat: float = Field(
        default=1005.0, description="Specific heat of air (J/kg*K)"
    )
    heat_loss_coeff: float = Field(
        default=0.001, description="Heat loss coefficient k (1/s)"
    )
    person_heat_w: float = Field(default=75.0, description="Heat output per person (W)")
    person_co2_m3_min: float = Field(
        default=0.005, description="CO2 exhalation per person (m3/min)"
    )
    ema_alpha: float = Field(default=0.1, description="EMA smoothing factor (0-1)")


# ═══════════════════════════════════════════════════════════════════
# Physical Constants
# ═══════════════════════════════════════════════════════════════════

_TEMP_MIN_C = -20.0
_TEMP_MAX_C = 60.0
_CO2_MIN_PPM = 350.0
_CO2_MAX_PPM = 10000.0
_MIN_VOLUME_M3 = 1.0  # Guard against zero-volume rooms


# ═══════════════════════════════════════════════════════════════════
# ODE Right-Hand Sides
# ═══════════════════════════════════════════════════════════════════


def _temperature_ode(
    T: np.ndarray,
    _t: float,
    k: float,
    T_outdoor: float,
    Q_hvac: float,
    Q_people: float,
    thermal_mass: float,
) -> list[float]:
    """Newton's law of cooling with HVAC and occupant heat sources.

    dT/dt = -k * (T - T_outdoor) + Q_hvac / (rho * V * c_p)
                                  + Q_people / (rho * V * c_p)

    Args:
        T: Current temperature state vector (single element).
        _t: Time (unused by the ODE itself, required by odeint).
        k: Heat loss coefficient (1/s).
        T_outdoor: Outdoor ambient temperature (C).
        Q_hvac: HVAC heat input (positive=heating, negative=cooling) in watts.
        Q_people: Total occupant heat output (watts).
        thermal_mass: rho * V * c_p (J/K) -- the room's thermal inertia.

    Returns:
        Time derivative of temperature [dT/dt].
    """
    thermal_mass = max(thermal_mass, 1.0)
    dTdt = -k * (T[0] - T_outdoor) + (Q_hvac + Q_people) / thermal_mass
    return [dTdt]


def _co2_ode(
    C: np.ndarray,
    _t: float,
    occupants: int,
    person_co2_m3_min: float,
    volume_m3: float,
    ventilation_rate_per_min: float,
    C_outdoor: float,
) -> list[float]:
    """CO2 mass-balance ODE.

    dC/dt = (occupants * person_co2_rate) / V
            - ventilation_rate * (C - C_outdoor)

    CO2 is tracked in ppm but the generation term uses m3/min, so we
    convert by multiplying the generation by 1e6 (ppm per unit volume
    fraction) to keep units consistent.

    Args:
        C: Current CO2 concentration state vector (ppm, single element).
        _t: Time (unused, required by odeint).
        occupants: Number of people in the room.
        person_co2_m3_min: CO2 exhalation rate per person (m3/min).
        volume_m3: Room volume (m3).
        ventilation_rate_per_min: Ventilation rate (1/min), derived from ACH.
        C_outdoor: Outdoor CO2 concentration (ppm).

    Returns:
        Time derivative of CO2 concentration [dC/dt] in ppm/min.
    """
    volume_m3 = max(volume_m3, _MIN_VOLUME_M3)
    generation_ppm_per_min = (occupants * person_co2_m3_min / volume_m3) * 1e6
    removal_ppm_per_min = ventilation_rate_per_min * (C[0] - C_outdoor)
    dCdt = generation_ppm_per_min - removal_ppm_per_min
    return [dCdt]


# ═══════════════════════════════════════════════════════════════════
# Public Simulation Functions
# ═══════════════════════════════════════════════════════════════════


def simulate_temperature_drift(
    state: RoomPhysicsState,
    area_m2: float,
    duration_minutes: int = 15,
    config: PhysicsSimConfig | None = None,
) -> list[tuple[float, float]]:
    """Simulate temperature drift using scipy ODE solver.

    Integrates Newton's law of cooling over the given duration,
    accounting for HVAC power and occupant body heat.

    Args:
        state: Current room physics state.
        area_m2: Room floor area (m2).
        duration_minutes: Simulation window length in minutes.
        config: Physics configuration (uses defaults if None).

    Returns:
        List of (time_minutes, temperature_c) sample points.
    """
    cfg = config or PhysicsSimConfig()
    area_m2 = max(area_m2, 0.1)
    duration_minutes = max(duration_minutes, 1)

    volume = area_m2 * cfg.ceiling_height_m
    volume = max(volume, _MIN_VOLUME_M3)
    thermal_mass = cfg.air_density * volume * cfg.air_specific_heat

    Q_people = state.occupant_count * cfg.person_heat_w

    # Time vector in seconds (odeint works in the unit of the ODE)
    duration_s = duration_minutes * 60.0
    n_points = max(duration_minutes + 1, 2)
    t_seconds = np.linspace(0.0, duration_s, n_points)

    T0 = [state.temperature_c]

    solution = odeint(
        _temperature_ode,
        T0,
        t_seconds,
        args=(
            cfg.heat_loss_coeff,
            cfg.outdoor_temp_c,
            state.hvac_power_w,
            Q_people,
            thermal_mass,
        ),
    )

    result: list[tuple[float, float]] = []
    for i, t_s in enumerate(t_seconds):
        temp = float(np.clip(solution[i, 0], _TEMP_MIN_C, _TEMP_MAX_C))
        result.append((round(t_s / 60.0, 4), round(temp, 4)))

    logger.debug(
        f"Temperature drift for {state.zone_id}: "
        f"{result[0][1]}C -> {result[-1][1]}C over {duration_minutes}min"
    )
    return result


def simulate_co2_drift(
    state: RoomPhysicsState,
    area_m2: float,
    duration_minutes: int = 15,
    config: PhysicsSimConfig | None = None,
) -> list[tuple[float, float]]:
    """Simulate CO2 accumulation using scipy ODE solver.

    Integrates the CO2 mass-balance equation accounting for occupant
    exhalation and mechanical ventilation.

    Args:
        state: Current room physics state.
        area_m2: Room floor area (m2).
        duration_minutes: Simulation window length in minutes.
        config: Physics configuration (uses defaults if None).

    Returns:
        List of (time_minutes, co2_ppm) sample points.
    """
    cfg = config or PhysicsSimConfig()
    area_m2 = max(area_m2, 0.1)
    duration_minutes = max(duration_minutes, 1)

    volume = area_m2 * cfg.ceiling_height_m
    volume = max(volume, _MIN_VOLUME_M3)

    # Convert ACH (air changes per hour) to a per-minute rate
    ventilation_rate_per_min = state.ventilation_ach / 60.0

    n_points = max(duration_minutes + 1, 2)
    t_minutes = np.linspace(0.0, float(duration_minutes), n_points)

    C0 = [state.co2_ppm]

    solution = odeint(
        _co2_ode,
        C0,
        t_minutes,
        args=(
            state.occupant_count,
            cfg.person_co2_m3_min,
            volume,
            ventilation_rate_per_min,
            cfg.outdoor_co2_ppm,
        ),
    )

    result: list[tuple[float, float]] = []
    for i, t_m in enumerate(t_minutes):
        co2 = float(np.clip(solution[i, 0], _CO2_MIN_PPM, _CO2_MAX_PPM))
        result.append((round(float(t_m), 4), round(co2, 2)))

    logger.debug(
        f"CO2 drift for {state.zone_id}: "
        f"{result[0][1]}ppm -> {result[-1][1]}ppm over {duration_minutes}min"
    )
    return result


def simulate_room_physics(
    state: RoomPhysicsState,
    area_m2: float,
    duration_minutes: int = 60,
    step_minutes: int = 1,
    config: PhysicsSimConfig | None = None,
) -> list[RoomPhysicsState]:
    """Full coupled physics simulation returning state at each timestep.

    Runs both temperature and CO2 ODEs in parallel over the requested
    window. Humidity is interpolated linearly toward equilibrium as a
    simplified model (full psychrometric coupling is out of scope).

    Args:
        state: Initial room physics state.
        area_m2: Room floor area (m2).
        duration_minutes: Total simulation window in minutes.
        step_minutes: Output resolution in minutes.
        config: Physics configuration (uses defaults if None).

    Returns:
        List of RoomPhysicsState snapshots, one per timestep.
    """
    cfg = config or PhysicsSimConfig()
    area_m2 = max(area_m2, 0.1)
    duration_minutes = max(duration_minutes, 1)
    step_minutes = max(step_minutes, 1)

    # Run the two ODE simulations over the full window
    temp_trajectory = simulate_temperature_drift(state, area_m2, duration_minutes, cfg)
    co2_trajectory = simulate_co2_drift(state, area_m2, duration_minutes, cfg)

    # Build lookup from time -> value (both have same time grid)
    temp_by_time: dict[float, float] = {t: v for t, v in temp_trajectory}
    co2_by_time: dict[float, float] = {t: v for t, v in co2_trajectory}

    # Determine the available time keys from the trajectories
    available_times = sorted(temp_by_time.keys())

    # Simplified humidity model: drift toward equilibrium
    # In a real building, humidity depends on ventilation and outdoor RH.
    # We model a slow regression toward 50% at a rate proportional to ACH.
    humidity_equilibrium = 50.0
    humidity_tau = max(60.0 / max(state.ventilation_ach, 0.1), 1.0)  # minutes

    states: list[RoomPhysicsState] = []
    for t_target in range(0, duration_minutes + 1, step_minutes):
        t_float = float(t_target)

        # Find closest available time point
        temp_val = _interpolate_trajectory(available_times, temp_by_time, t_float)
        co2_val = _interpolate_trajectory(
            sorted(co2_by_time.keys()), co2_by_time, t_float
        )

        # Humidity interpolation
        humidity_frac = 1.0 - np.exp(-t_float / humidity_tau)
        humidity = (
            state.humidity_pct
            + (humidity_equilibrium - state.humidity_pct) * humidity_frac
        )
        humidity = float(np.clip(humidity, 0.0, 100.0))

        states.append(
            RoomPhysicsState(
                zone_id=state.zone_id,
                temperature_c=round(temp_val, 2),
                co2_ppm=round(co2_val, 1),
                humidity_pct=round(humidity, 1),
                occupant_count=state.occupant_count,
                hvac_power_w=state.hvac_power_w,
                ventilation_ach=state.ventilation_ach,
            )
        )

    logger.debug(
        f"Room physics for {state.zone_id}: {len(states)} steps "
        f"over {duration_minutes}min"
    )
    return states


# ═══════════════════════════════════════════════════════════════════
# EMA Smoothing
# ═══════════════════════════════════════════════════════════════════


def ema_smooth(values: list[float], alpha: float = 0.1) -> list[float]:
    """Apply Exponential Moving Average smoothing to a sequence.

    ema(t) = alpha * value(t) + (1 - alpha) * ema(t-1)

    Args:
        values: Raw time-series values.
        alpha: Smoothing factor in (0, 1]. Higher values track faster.

    Returns:
        EMA-smoothed values (same length as input). Returns empty list
        if input is empty.
    """
    if not values:
        return []

    alpha = float(np.clip(alpha, 0.001, 1.0))
    smoothed: list[float] = [values[0]]

    for i in range(1, len(values)):
        ema_val = alpha * values[i] + (1.0 - alpha) * smoothed[i - 1]
        smoothed.append(round(ema_val, 6))

    return smoothed


# ═══════════════════════════════════════════════════════════════════
# Edge Fusion
# ═══════════════════════════════════════════════════════════════════


def edge_fusion_blend(
    simulated: float,
    sensor_reading: float | None,
    sensor_confidence: float = 0.0,
) -> float:
    """Blend a simulated value with a real sensor reading.

    blend = confidence * sensor + (1 - confidence) * simulated

    When the sensor reading is None or confidence is 0, the simulated
    value is returned unchanged.

    Args:
        simulated: Physics-engine simulated value.
        sensor_reading: Actual sensor measurement (None if unavailable).
        sensor_confidence: Trust weight for the sensor, in [0, 1].

    Returns:
        Blended value.
    """
    if sensor_reading is None or sensor_confidence <= 0.0:
        return simulated

    confidence = float(np.clip(sensor_confidence, 0.0, 1.0))
    blended = confidence * sensor_reading + (1.0 - confidence) * simulated
    return round(blended, 6)


# ═══════════════════════════════════════════════════════════════════
# DataStore Integration
# ═══════════════════════════════════════════════════════════════════


def get_current_physics_state(zone_id: str) -> RoomPhysicsState:
    """Build the current physics state for a zone from the DataStore.

    Reads the latest comfort and occupancy data. Falls back to sensible
    defaults when data is not yet available. Validates the zone_id against
    the building definition.

    Args:
        zone_id: Unique zone identifier.

    Returns:
        RoomPhysicsState populated from the latest store data.
    """
    zone = get_zone_by_id(zone_id)
    if zone is None:
        logger.warning(f"Unknown zone '{zone_id}', returning default state")
        return RoomPhysicsState(zone_id=zone_id)

    # Defaults
    temperature = 22.0
    co2 = 420.0
    humidity = 50.0
    occupants = 0
    hvac_power = 0.0
    ventilation = 2.0 if zone.has_hvac else 0.5

    # ── Comfort data ──────────────────────────────
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df is not None and not comfort_df.empty:
        if "timestamp" in comfort_df.columns:
            comfort_df = comfort_df.sort_values("timestamp")
        latest = comfort_df.iloc[-1]
        temperature = float(latest.get("temperature_c", temperature))
        co2 = float(latest.get("co2_ppm", co2))
        humidity = float(latest.get("humidity_pct", humidity))

    # ── Occupancy data ────────────────────────────
    occ_df = store.get_zone_data("occupancy", zone_id)
    if occ_df is not None and not occ_df.empty:
        if "timestamp" in occ_df.columns:
            occ_df = occ_df.sort_values("timestamp")
        latest_occ = occ_df.iloc[-1]
        occupants = int(latest_occ.get("occupant_count", occupants))

    # ── Energy data (approximate HVAC power) ──────
    energy_df = store.get_zone_data("energy", zone_id)
    if energy_df is not None and not energy_df.empty:
        if "timestamp" in energy_df.columns:
            energy_df = energy_df.sort_values("timestamp")
        latest_energy = energy_df.iloc[-1]
        # Convert kWh (per interval) to approximate watts
        kwh = float(latest_energy.get("hvac_kwh", 0.0))
        hvac_power = kwh * 4000.0  # 15-min interval -> W (kwh * 4 * 1000)

    logger.debug(
        f"Physics state for {zone_id}: T={temperature}C, CO2={co2}ppm, occ={occupants}"
    )

    return RoomPhysicsState(
        zone_id=zone_id,
        temperature_c=temperature,
        co2_ppm=co2,
        humidity_pct=humidity,
        occupant_count=occupants,
        hvac_power_w=hvac_power,
        ventilation_ach=ventilation,
    )


def compute_smoothed_financial_bleed(
    zone_id: str,
    window_minutes: int = 60,
    config: PhysicsSimConfig | None = None,
) -> float:
    """Compute EMA-smoothed financial bleed rate for a zone.

    Retrieves historical financial bleed values from the store (computed
    by the AFI engine) and applies EMA smoothing to eliminate jitter and
    random jumps.  If no historical data is available, falls back to a
    single-point estimate from the current AFI engine output.

    Args:
        zone_id: Unique zone identifier.
        window_minutes: Look-back window for historical bleed values.
        config: Physics configuration (for EMA alpha).

    Returns:
        Smoothed financial bleed rate in EUR/hr.
    """
    cfg = config or PhysicsSimConfig()

    # Try to get historical bleed from the store
    bleed_df = store.get_zone_data("financial_bleed", zone_id)
    bleed_values: list[float] = []

    if bleed_df is not None and not bleed_df.empty:
        if "timestamp" in bleed_df.columns:
            bleed_df = bleed_df.sort_values("timestamp")
            # Filter to the look-back window
            if len(bleed_df) > 0:
                latest_ts = bleed_df["timestamp"].iloc[-1]
                cutoff = latest_ts - np.timedelta64(window_minutes, "m")
                bleed_df = bleed_df[bleed_df["timestamp"] >= cutoff]

        col = "total_bleed_eur_hr"
        if col in bleed_df.columns:
            bleed_values = bleed_df[col].dropna().tolist()

    # If we have historical data, smooth it
    if len(bleed_values) >= 2:
        smoothed = ema_smooth(bleed_values, alpha=cfg.ema_alpha)
        result = smoothed[-1] if smoothed else 0.0
        logger.debug(
            f"Smoothed bleed for {zone_id}: {result:.4f} EUR/hr "
            f"(from {len(bleed_values)} points)"
        )
        return round(result, 4)

    # Fallback: compute a single-point estimate from the AFI engine
    try:
        from core.afi_engine import compute_financial_bleed as afi_bleed

        afi_cfg_kwargs = {
            "cost_per_kwh": DEFAULT_AFI_CONFIG.cost_per_kwh,
            "avg_hourly_wage": DEFAULT_AFI_CONFIG.avg_hourly_wage,
            "impact_factor": DEFAULT_AFI_CONFIG.impact_factor,
        }
        from config.afi_config import AFIConfig as AFICfg

        bleed_result = afi_bleed(zone_id, AFICfg(**afi_cfg_kwargs))
        result = bleed_result.total_bleed_eur_hr
        logger.debug(
            f"Single-point bleed for {zone_id}: {result:.4f} EUR/hr (no history)"
        )
        return round(result, 4)
    except Exception as exc:
        logger.warning(f"Could not compute bleed for {zone_id}: {exc}")
        return 0.0


# ═══════════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════════


def _interpolate_trajectory(
    sorted_times: list[float],
    values_by_time: dict[float, float],
    target_time: float,
) -> float:
    """Linear interpolation into a trajectory dictionary.

    Args:
        sorted_times: Sorted list of available time keys.
        values_by_time: Mapping from time to value.
        target_time: The time to look up.

    Returns:
        Interpolated (or nearest) value.
    """
    if not sorted_times:
        return 0.0

    # Exact match
    if target_time in values_by_time:
        return values_by_time[target_time]

    # Clamp to bounds
    if target_time <= sorted_times[0]:
        return values_by_time[sorted_times[0]]
    if target_time >= sorted_times[-1]:
        return values_by_time[sorted_times[-1]]

    # Binary search for bracketing interval
    idx = int(np.searchsorted(sorted_times, target_time))
    t_lo = sorted_times[idx - 1]
    t_hi = sorted_times[idx]
    v_lo = values_by_time[t_lo]
    v_hi = values_by_time[t_hi]

    dt = t_hi - t_lo
    if dt == 0:
        return v_lo

    frac = (target_time - t_lo) / dt
    return v_lo + frac * (v_hi - v_lo)
