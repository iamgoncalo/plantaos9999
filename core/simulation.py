"""What-if simulation engine for catastrophic and operational scenarios.

Simulates events like fire, open windows, mass entry, and HVAC failure.
Computes cascade effects using AFI formulas and predicts financial damage
over configurable time horizons.
"""

from __future__ import annotations

import math
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field

from config.afi_config import AFIConfig, DEFAULT_AFI_CONFIG
from config.building import get_zone_by_id
from data.physical_ai_bridge import (
    PhysicsSimConfig,
    RoomPhysicsState,
    simulate_room_physics,
)
from data.store import store


class SimulationEvent(BaseModel):
    """A triggered what-if event."""

    event_type: str = Field(description="fire, open_window, mass_entry, hvac_failure")
    zone_id: str
    intensity: float = Field(default=0.8, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class SimulationStep(BaseModel):
    """A single timestep in the simulation timeline."""

    step: int
    minutes_elapsed: int
    temperature_c: float = 22.0
    co2_ppm: float = 500.0
    occupant_count: int = 0
    distortion: float = 1.0
    financial_damage_eur: float = 0.0
    cumulative_cost_eur: float = 0.0
    freedom: float = 1.0


class SimulationResult(BaseModel):
    """Complete simulation result with timeline and summary."""

    event: SimulationEvent
    timeline: list[SimulationStep] = Field(default_factory=list)
    total_financial_damage_eur: float = 0.0
    evacuation_time_seconds: float | None = None
    zones_affected: list[str] = Field(default_factory=list)
    summary: str = ""


def simulate_event(
    event: SimulationEvent,
    duration_hours: int = 24,
    step_minutes: int = 15,
    config: AFIConfig | None = None,
) -> SimulationResult:
    """Run a what-if simulation for a triggered event.

    Args:
        event: The event to simulate.
        duration_hours: Duration of simulation in hours.
        step_minutes: Time between simulation steps in minutes.
        config: AFI configuration override.

    Returns:
        SimulationResult with timeline and financial damage.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    handlers = {
        "fire": _simulate_fire,
        "open_window": _simulate_open_window,
        "mass_entry": _simulate_mass_entry,
        "hvac_failure": _simulate_hvac_failure,
        "hvac_night_off": _simulate_hvac_night_off,
        "presence_sensors": _simulate_presence_sensors,
        "setpoint_adjust": _simulate_setpoint_adjust,
        "zone_consolidation": _simulate_zone_consolidation,
    }
    handler = handlers.get(event.event_type)
    if handler is None:
        logger.warning(f"Unknown event type: {event.event_type}")
        return SimulationResult(event=event, summary="Unknown event type")

    return handler(event, duration_hours, step_minutes, cfg)


def _simulate_fire(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate a fire outbreak in a zone."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    capacity = zone.capacity if zone else 30
    area = zone.area_m2 if zone else 40.0

    # Get current occupancy
    occ_df = store.get_zone_data("occupancy", event.zone_id)
    current_occ = 0
    if occ_df is not None and not occ_df.empty:
        current_occ = int(
            occ_df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
        )
    n_people = max(current_occ, int(capacity * 0.5))

    # Evacuation time: distance / speed + delay per person
    room_diagonal = math.sqrt(area) * 1.4  # approximate diagonal
    evac_time = room_diagonal / 1.2 + n_people * 0.5  # seconds

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    # Affected zones: the fire zone + adjacent
    from core.afi_engine import _ZONE_ADJACENCY

    neighbors = _ZONE_ADJACENCY.get(event.zone_id, [])
    affected = [event.zone_id] + neighbors[:3]

    for i in range(n_steps):
        minutes = i * step_minutes
        # Temperature: spikes rapidly then stabilizes
        temp = 22.0 + event.intensity * 800 * (1 - math.exp(-minutes / 10))
        temp = min(temp, 900.0)
        # CO2: spikes with combustion
        co2 = 500 + event.intensity * 10000 * (1 - math.exp(-minutes / 15))
        # Occupancy: drops to 0 after evacuation
        occ = n_people if minutes < evac_time / 60 else 0
        # Distortion: infinite for fire
        D = 1000.0 if minutes < 120 else 500.0 * math.exp(-(minutes - 120) / 360)
        D = max(1.0, D)
        # Financial damage
        asset_damage = (
            (cfg.asset_value_eur * area / 800)
            * event.intensity
            * min(1.0, minutes / 60)
        )
        human_cost = n_people * cfg.avg_hourly_wage * (evac_time / 3600)
        step_cost = (asset_damage + human_cost) * step_minutes / (duration_hours * 60)
        cumulative += step_cost

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(temp, 1),
                co2_ppm=round(co2, 0),
                occupant_count=occ,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 2),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        evacuation_time_seconds=round(evac_time, 1),
        zones_affected=affected,
        summary=(
            f"Fire in {zone_name}: {n_people} evacuated in "
            f"{evac_time:.0f}s, \u20ac{cumulative:.0f} damage"
        ),
    )


def _simulate_open_window(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate an open window causing temperature drift using ODE physics."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0
    volume = area * cfg.ceiling_height_m

    # Get outdoor temperature
    weather_df = store.get("weather")
    outdoor_temp = 12.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 12.0)
        )

    # Open window: high ventilation ACH, no HVAC compensation
    window_ach = 4.0 + event.intensity * 8.0
    initial_state = RoomPhysicsState(
        zone_id=event.zone_id,
        temperature_c=cfg.optimal_temperature_c,
        co2_ppm=500.0,
        humidity_pct=50.0,
        occupant_count=0,
        hvac_power_w=0.0,
        ventilation_ach=window_ach,
    )
    physics_config = PhysicsSimConfig(
        outdoor_temp_c=outdoor_temp,
        heat_loss_coeff=0.001 + event.intensity * 0.003,
    )

    duration_minutes = duration_hours * 60
    try:
        physics_states = simulate_room_physics(
            initial_state, area, duration_minutes, step_minutes, physics_config
        )
    except Exception as exc:
        logger.warning(f"ODE failed for open_window, using analytical fallback: {exc}")
        return _simulate_open_window_analytical(
            event, duration_hours, step_minutes, cfg
        )

    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i, ps in enumerate(physics_states):
        minutes = i * step_minutes
        drift = abs(ps.temperature_c - cfg.optimal_temperature_c)
        q_kwh = (cfg.air_density * volume * cfg.air_specific_heat * drift) / 3600
        hvac_cost = q_kwh / cfg.hvac_efficiency * cfg.cost_per_kwh
        step_cost = hvac_cost * (step_minutes / 60)
        cumulative += step_cost
        D = 1.0 + drift / 4.0

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(ps.temperature_c, 1),
                co2_ppm=round(ps.co2_ppm, 0),
                occupant_count=0,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Open window in {zone_name}: "
            f"\u20ac{cumulative:.2f} HVAC waste over {duration_hours}h"
        ),
    )


def _simulate_open_window_analytical(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Analytical fallback for open window simulation."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0
    volume = area * cfg.ceiling_height_m

    weather_df = store.get("weather")
    outdoor_temp = 12.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 12.0)
        )

    indoor_temp_start = cfg.optimal_temperature_c
    tau = volume * cfg.air_density * cfg.air_specific_heat / (50 * event.intensity + 1)

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i in range(n_steps):
        minutes = i * step_minutes
        hours = minutes / 60.0
        delta_t = indoor_temp_start - outdoor_temp
        current_temp = outdoor_temp + delta_t * math.exp(-hours / max(tau, 0.1))
        drift = abs(current_temp - indoor_temp_start)
        q_kwh = (cfg.air_density * volume * cfg.air_specific_heat * drift) / 3600
        hvac_cost = q_kwh / cfg.hvac_efficiency * cfg.cost_per_kwh
        step_cost = hvac_cost * (step_minutes / 60)
        cumulative += step_cost
        D = 1.0 + drift / 4.0

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(current_temp, 1),
                co2_ppm=500,
                occupant_count=0,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Open window in {zone_name}: "
            f"\u20ac{cumulative:.2f} HVAC waste over {duration_hours}h"
        ),
    )


def _simulate_mass_entry(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate mass entry of people."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    capacity = zone.capacity if zone else 30
    n_people = int(500 * event.intensity)

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i in range(n_steps):
        minutes = i * step_minutes
        # People arrive in first 30 min, then slowly leave
        if minutes < 30:
            current_occ = int(n_people * minutes / 30)
        else:
            current_occ = int(n_people * math.exp(-(minutes - 30) / 180))

        ratio = current_occ / max(capacity, 1)
        co2 = 400 + current_occ * 15  # ~15 ppm per person
        D = 1.0 + max(0, ratio - 0.8) * 5

        loss = (
            (1 - min(100, 50 + ratio * 30) / 100)
            * current_occ
            * cfg.avg_hourly_wage
            * cfg.impact_factor
        )
        step_cost = loss * step_minutes / 60
        cumulative += step_cost

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=22 + current_occ * 0.02,
                co2_ppm=round(min(co2, 5000), 0),
                occupant_count=current_occ,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    from core.afi_engine import _ZONE_ADJACENCY

    neighbors = _ZONE_ADJACENCY.get(event.zone_id, [])

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        zones_affected=[event.zone_id] + neighbors[:2],
        summary=(
            f"Mass entry in {zone_name}: "
            f"{n_people} people, \u20ac{cumulative:.2f} productivity loss"
        ),
    )


def _simulate_hvac_failure(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate HVAC failure using ODE physics."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0

    weather_df = store.get("weather")
    outdoor_temp = 12.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 12.0)
        )

    # Get current occupancy
    occ_df = store.get_zone_data("occupancy", event.zone_id)
    n_people = 0
    if occ_df is not None and not occ_df.empty:
        n_people = int(
            occ_df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
        )

    # HVAC is OFF, minimal natural ventilation
    initial_state = RoomPhysicsState(
        zone_id=event.zone_id,
        temperature_c=cfg.optimal_temperature_c,
        co2_ppm=500.0,
        humidity_pct=50.0,
        occupant_count=n_people,
        hvac_power_w=0.0,
        ventilation_ach=0.5,
    )
    physics_config = PhysicsSimConfig(
        outdoor_temp_c=outdoor_temp,
        heat_loss_coeff=0.0005,
    )

    duration_minutes = duration_hours * 60
    try:
        physics_states = simulate_room_physics(
            initial_state, area, duration_minutes, step_minutes, physics_config
        )
    except Exception as exc:
        logger.warning(f"ODE failed for hvac_failure, using analytical fallback: {exc}")
        return _simulate_hvac_failure_analytical(
            event, duration_hours, step_minutes, cfg
        )

    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i, ps in enumerate(physics_states):
        minutes = i * step_minutes
        deviation = abs(ps.temperature_c - cfg.optimal_temperature_c)
        loss = (deviation / 10) * n_people * cfg.avg_hourly_wage * cfg.impact_factor
        step_cost = loss * step_minutes / 60
        cumulative += step_cost
        D = 1.0 + deviation / 4

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(ps.temperature_c, 1),
                co2_ppm=round(ps.co2_ppm, 0),
                occupant_count=n_people,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"HVAC failure in {zone_name}: "
            f"\u20ac{cumulative:.2f} over {duration_hours}h"
        ),
    )


def _simulate_hvac_failure_analytical(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Analytical fallback for HVAC failure simulation."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id

    weather_df = store.get("weather")
    outdoor_temp = 12.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 12.0)
        )

    occ_df = store.get_zone_data("occupancy", event.zone_id)
    n_people = 0
    if occ_df is not None and not occ_df.empty:
        n_people = int(
            occ_df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
        )

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0
    indoor_start = cfg.optimal_temperature_c

    for i in range(n_steps):
        minutes = i * step_minutes
        hours = minutes / 60.0
        tau = 8.0
        delta = indoor_start - outdoor_temp
        current_temp = outdoor_temp + delta * math.exp(-hours / tau)
        deviation = abs(current_temp - cfg.optimal_temperature_c)
        loss = (deviation / 10) * n_people * cfg.avg_hourly_wage * cfg.impact_factor
        step_cost = loss * step_minutes / 60
        cumulative += step_cost
        D = 1.0 + deviation / 4

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(current_temp, 1),
                co2_ppm=500 + int(deviation * 20),
                occupant_count=n_people,
                distortion=round(D, 2),
                financial_damage_eur=round(step_cost, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=round(1.0 / D, 4),
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(cumulative, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"HVAC failure in {zone_name}: "
            f"\u20ac{cumulative:.2f} over {duration_hours}h"
        ),
    )


# ═══════════════════════════════════════════════
# Optimization Scenarios (ROI-focused)
# ═══════════════════════════════════════════════


def _simulate_hvac_night_off(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate turning off HVAC during night hours (22:00-06:00).

    Estimates energy savings from not running HVAC during unoccupied
    nighttime hours, using the ODE to show temperature drift.
    """
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0

    weather_df = store.get("weather")
    outdoor_temp = 10.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 10.0)
        )

    # Simulate 8 hours of HVAC off (22:00-06:00)
    night_hours = 8
    initial_state = RoomPhysicsState(
        zone_id=event.zone_id,
        temperature_c=cfg.optimal_temperature_c,
        co2_ppm=420.0,
        humidity_pct=50.0,
        occupant_count=0,
        hvac_power_w=0.0,
        ventilation_ach=0.3,
    )
    physics_config = PhysicsSimConfig(
        outdoor_temp_c=outdoor_temp,
        heat_loss_coeff=0.0003,
    )

    try:
        physics_states = simulate_room_physics(
            initial_state, area, night_hours * 60, step_minutes, physics_config
        )
    except Exception:
        physics_states = []

    # Estimate savings: typical HVAC power ~2kW for this zone at night
    hvac_kw = 2.0 * (area / 50.0)
    nightly_savings = hvac_kw * night_hours * cfg.cost_per_kwh
    monthly_savings = nightly_savings * 22

    timeline: list[SimulationStep] = []
    cumulative_savings = 0.0

    n_steps = (duration_hours * 60) // step_minutes
    for i in range(n_steps):
        minutes = i * step_minutes
        if i < len(physics_states):
            temp = physics_states[i].temperature_c
            co2 = physics_states[i].co2_ppm
        else:
            temp = outdoor_temp + (cfg.optimal_temperature_c - outdoor_temp) * 0.3
            co2 = 420.0

        step_savings = nightly_savings / max(n_steps, 1)
        cumulative_savings += step_savings

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=round(temp, 1),
                co2_ppm=round(co2, 0),
                occupant_count=0,
                distortion=1.0,
                financial_damage_eur=round(step_savings, 4),
                cumulative_cost_eur=round(cumulative_savings, 2),
                freedom=1.0,
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(monthly_savings, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Desligar AVAC à noite em {zone_name}: "
            f"poupança \u20ac{monthly_savings:.0f}/mês"
        ),
    )


def _simulate_presence_sensors(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate installing presence sensors for demand-based HVAC."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0

    empty_hours_per_day = 4.0
    hvac_kw = 2.0 * (area / 50.0)
    daily_savings = hvac_kw * empty_hours_per_day * cfg.cost_per_kwh
    monthly_savings = daily_savings * 22
    sensor_cost = 150.0

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i in range(n_steps):
        minutes = i * step_minutes
        step_saving = monthly_savings / max(n_steps, 1)
        cumulative += step_saving

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=cfg.optimal_temperature_c,
                co2_ppm=500.0,
                occupant_count=0,
                distortion=1.0,
                financial_damage_eur=round(step_saving, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=1.0,
            )
        )

    payback_months = sensor_cost / monthly_savings if monthly_savings > 0 else 99

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(monthly_savings, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Sensores de presença em {zone_name}: "
            f"\u20ac{monthly_savings:.0f}/mês, payback {payback_months:.0f} meses"
        ),
    )


def _simulate_setpoint_adjust(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate raising HVAC setpoint by 2°C in summer."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0

    hvac_kw = 2.0 * (area / 50.0)
    daily_hvac_cost = hvac_kw * 10 * cfg.cost_per_kwh
    daily_savings = daily_hvac_cost * 0.06
    monthly_savings = daily_savings * 22

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i in range(n_steps):
        minutes = i * step_minutes
        step_saving = monthly_savings / max(n_steps, 1)
        cumulative += step_saving

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=cfg.optimal_temperature_c + 2.0,
                co2_ppm=500.0,
                occupant_count=0,
                distortion=1.0,
                financial_damage_eur=round(step_saving, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=0.95,
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(monthly_savings, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Ajustar setpoint +2°C em {zone_name}: "
            f"\u20ac{monthly_savings:.0f}/mês poupança"
        ),
    )


def _simulate_zone_consolidation(
    event: SimulationEvent,
    duration_hours: int,
    step_minutes: int,
    cfg: AFIConfig,
) -> SimulationResult:
    """Simulate consolidating underused zones to save HVAC cost."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0

    idle_hours = 6.0
    hvac_kw = 2.0 * (area / 50.0)
    daily_savings = hvac_kw * idle_hours * cfg.cost_per_kwh
    monthly_savings = daily_savings * 22

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0

    for i in range(n_steps):
        minutes = i * step_minutes
        step_saving = monthly_savings / max(n_steps, 1)
        cumulative += step_saving

        timeline.append(
            SimulationStep(
                step=i,
                minutes_elapsed=minutes,
                temperature_c=cfg.optimal_temperature_c,
                co2_ppm=420.0,
                occupant_count=0,
                distortion=1.0,
                financial_damage_eur=round(step_saving, 4),
                cumulative_cost_eur=round(cumulative, 2),
                freedom=1.0,
            )
        )

    return SimulationResult(
        event=event,
        timeline=timeline,
        total_financial_damage_eur=round(monthly_savings, 2),
        zones_affected=[event.zone_id],
        summary=(
            f"Consolidar {zone_name}: "
            f"\u20ac{monthly_savings:.0f}/mês ao desligar AVAC fora de uso"
        ),
    )
