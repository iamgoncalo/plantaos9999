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
    """Simulate an open window causing temperature drift."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id
    area = zone.area_m2 if zone else 40.0
    volume = area * cfg.ceiling_height_m

    # Get outdoor temperature
    weather_df = store.get("weather")
    outdoor_temp = 12.0  # Default March Aveiro
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
        # Temperature drifts toward outdoor with time constant tau
        delta_t = indoor_temp_start - outdoor_temp
        current_temp = outdoor_temp + delta_t * math.exp(-hours / max(tau, 0.1))
        drift = abs(current_temp - indoor_temp_start)

        # HVAC cost grows exponentially as it compensates
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
    """Simulate HVAC failure causing temperature drift."""
    zone = get_zone_by_id(event.zone_id)
    zone_name = zone.name if zone else event.zone_id

    weather_df = store.get("weather")
    outdoor_temp = 12.0
    if weather_df is not None and not weather_df.empty:
        outdoor_temp = float(
            weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c", 12.0)
        )

    n_steps = (duration_hours * 60) // step_minutes
    timeline: list[SimulationStep] = []
    cumulative = 0.0
    indoor_start = cfg.optimal_temperature_c

    for i in range(n_steps):
        minutes = i * step_minutes
        hours = minutes / 60.0
        # Slow drift without HVAC
        tau = 8.0  # hours
        delta = indoor_start - outdoor_temp
        current_temp = outdoor_temp + delta * math.exp(-hours / tau)
        deviation = abs(current_temp - cfg.optimal_temperature_c)

        occ_df = store.get_zone_data("occupancy", event.zone_id)
        n_people = 0
        if occ_df is not None and not occ_df.empty:
            n_people = int(
                occ_df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
            )

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
