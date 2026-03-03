"""Zone state aggregation and spatial path computation.

Aggregates sensor readings into per-zone state summaries and computes
spatial relationships between zones for correlation analysis.
"""

from __future__ import annotations

import random
from datetime import datetime

import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from config.building import get_zones_by_floor
from config.settings import settings
from config.thresholds import evaluate_comfort
from core.freedom_index import compute_zone_freedom
from data.store import store


class ZoneState(BaseModel):
    """Snapshot of a zone's current state."""

    zone_id: str
    timestamp: datetime
    temperature_c: float | None = None
    humidity_pct: float | None = None
    co2_ppm: float | None = None
    illuminance_lux: float | None = None
    occupant_count: int = 0
    total_energy_kwh: float = 0.0
    freedom_index: float = 0.0
    status: str = "unknown"


class FloorState(BaseModel):
    """Aggregated state for a building floor."""

    floor: int
    timestamp: datetime
    zones: list[ZoneState] = Field(default_factory=list)
    avg_temperature: float = 0.0
    avg_humidity: float = 0.0
    total_occupancy: int = 0
    total_energy_kwh: float = 0.0


class BuildingState(BaseModel):
    """Aggregated state for the entire building."""

    timestamp: datetime
    floors: list[FloorState] = Field(default_factory=list)
    total_occupancy: int = 0
    total_energy_kwh: float = 0.0
    avg_freedom_index: float = 0.0
    active_alerts: int = 0


def aggregate_zone_state(
    zone_id: str,
    timestamp: datetime | None = None,
) -> ZoneState:
    """Aggregate all metrics into a single zone state snapshot.

    Args:
        zone_id: Zone to aggregate.
        timestamp: Specific timestamp. Defaults to latest.

    Returns:
        ZoneState with all current metrics.
    """
    now = timestamp or datetime.now()

    # Get latest comfort data
    comfort_df = store.get_zone_data("comfort", zone_id)
    temp_c = None
    hum_pct = None
    co2 = None
    lux = None

    if comfort_df is not None and not comfort_df.empty:
        latest_comfort = comfort_df.sort_values("timestamp").iloc[-1]
        temp_c = (
            float(latest_comfort.get("temperature_c", 0))
            if pd.notna(latest_comfort.get("temperature_c"))
            else None
        )
        hum_pct = (
            float(latest_comfort.get("humidity_pct", 0))
            if pd.notna(latest_comfort.get("humidity_pct"))
            else None
        )
        co2 = (
            float(latest_comfort.get("co2_ppm", 0))
            if pd.notna(latest_comfort.get("co2_ppm"))
            else None
        )
        lux = (
            float(latest_comfort.get("illuminance_lux", 0))
            if pd.notna(latest_comfort.get("illuminance_lux"))
            else None
        )

    # Get latest occupancy
    occ_df = store.get_zone_data("occupancy", zone_id)
    occ_count = 0
    if occ_df is not None and not occ_df.empty:
        latest_occ = occ_df.sort_values("timestamp").iloc[-1]
        occ_count = int(latest_occ.get("occupant_count", 0))

    # Get latest energy (sum over last reading period)
    energy_df = store.get_zone_data("energy", zone_id)
    total_energy = 0.0
    if energy_df is not None and not energy_df.empty:
        latest_energy = energy_df.sort_values("timestamp").iloc[-1]
        total_energy = float(latest_energy.get("total_kwh", 0))

    # Compute freedom index
    freedom = compute_zone_freedom(zone_id)

    # Determine status based on worst comfort metric
    status = _classify_zone_status(temp_c, hum_pct, co2, lux)

    return ZoneState(
        zone_id=zone_id,
        timestamp=now,
        temperature_c=temp_c,
        humidity_pct=hum_pct,
        co2_ppm=co2,
        illuminance_lux=lux,
        occupant_count=occ_count,
        total_energy_kwh=round(total_energy, 4),
        freedom_index=freedom,
        status=status,
    )


def compute_floor_state(floor: int) -> FloorState:
    """Aggregate all zones on a floor into a floor state.

    Args:
        floor: Floor number (0 or 1).

    Returns:
        FloorState with aggregated metrics.
    """
    now = datetime.now()
    zones = get_zones_by_floor(floor)
    monitored = [z for z in zones if z.has_sensors]

    zone_states: list[ZoneState] = []
    temps: list[float] = []
    humidities: list[float] = []
    total_occ = 0
    total_energy = 0.0

    for zone in monitored:
        state = aggregate_zone_state(zone.id)
        zone_states.append(state)

        if state.temperature_c is not None:
            temps.append(state.temperature_c)
        if state.humidity_pct is not None:
            humidities.append(state.humidity_pct)
        total_occ += state.occupant_count
        total_energy += state.total_energy_kwh

    return FloorState(
        floor=floor,
        timestamp=now,
        zones=zone_states,
        avg_temperature=round(float(np.mean(temps)), 1) if temps else 0.0,
        avg_humidity=round(float(np.mean(humidities)), 1) if humidities else 0.0,
        total_occupancy=total_occ,
        total_energy_kwh=round(total_energy, 4),
    )


def compute_building_state() -> BuildingState:
    """Aggregate all floors into a building-wide state summary.

    Returns:
        BuildingState with building-level aggregated metrics.
    """
    now = datetime.now()

    floor_states = [
        compute_floor_state(0),
        compute_floor_state(1),
    ]

    total_occ = sum(f.total_occupancy for f in floor_states)
    total_energy = sum(f.total_energy_kwh for f in floor_states)

    # Demo mode: inject anomalies for visible alerts during demos
    if settings.DEMO_MODE:
        _inject_demo_anomalies(floor_states)

    # Average freedom index across all monitored zones
    all_zone_states = [z for f in floor_states for z in f.zones]
    freedom_scores = [z.freedom_index for z in all_zone_states if z.freedom_index > 0]
    avg_freedom = float(np.mean(freedom_scores)) if freedom_scores else 0.0

    # Count active alerts (zones with warning/critical status)
    active_alerts = sum(
        1 for z in all_zone_states if z.status in ("warning", "critical")
    )

    logger.info(
        f"Building state: {total_occ} occupants, {total_energy:.1f} kWh, "
        f"freedom={avg_freedom:.1f}, alerts={active_alerts}"
    )

    return BuildingState(
        timestamp=now,
        floors=floor_states,
        total_occupancy=total_occ,
        total_energy_kwh=round(total_energy, 4),
        avg_freedom_index=round(avg_freedom, 1),
        active_alerts=active_alerts,
    )


def _classify_zone_status(
    temp: float | None,
    humidity: float | None,
    co2: float | None,
    lux: float | None,
) -> str:
    """Classify zone status based on comfort metrics.

    Args:
        temp: Temperature in °C.
        humidity: Humidity in %.
        co2: CO2 in ppm.
        lux: Illuminance in lux.

    Returns:
        Status: 'optimal', 'acceptable', 'warning', or 'critical'.
    """
    statuses = []

    if temp is not None:
        statuses.append(evaluate_comfort("temperature", temp))
    if humidity is not None:
        statuses.append(evaluate_comfort("humidity", humidity))
    if co2 is not None:
        statuses.append(evaluate_comfort("co2", co2))
    if lux is not None:
        statuses.append(evaluate_comfort("illuminance", lux))

    if not statuses:
        return "unknown"

    # Return worst status
    severity_order = {
        "critical": 3,
        "warning": 2,
        "acceptable": 1,
        "optimal": 0,
        "unknown": -1,
    }
    worst = max(statuses, key=lambda s: severity_order.get(s, -1))
    return worst


def _inject_demo_anomalies(floor_states: list[FloorState]) -> None:
    """Inject random anomalies into zone states for demo visibility.

    Randomly selects 2-3 zones and pushes their metrics into
    warning/critical range based on DEMO_ANOMALY_RATE.

    Args:
        floor_states: Floor states to mutate in-place.
    """
    all_zones = [z for f in floor_states for z in f.zones]
    if not all_zones:
        return

    n_anomalies = random.randint(2, 3)
    candidates = [z for z in all_zones if z.status not in ("warning", "critical")]
    targets = random.sample(candidates, min(n_anomalies, len(candidates)))

    for zone in targets:
        if random.random() > settings.DEMO_ANOMALY_RATE:
            continue
        anomaly_type = random.choice(["co2", "temperature", "energy"])
        if anomaly_type == "co2" and zone.co2_ppm is not None:
            zone.co2_ppm = random.uniform(1200, 1800)
            zone.status = "critical"
            zone.freedom_index = max(10, zone.freedom_index - 40)
        elif anomaly_type == "temperature" and zone.temperature_c is not None:
            zone.temperature_c = random.choice(
                [random.uniform(28, 32), random.uniform(14, 17)]
            )
            zone.status = "warning"
            zone.freedom_index = max(20, zone.freedom_index - 30)
        elif anomaly_type == "energy":
            zone.total_energy_kwh *= random.uniform(2.5, 4.0)
            zone.status = "warning"
            zone.freedom_index = max(25, zone.freedom_index - 25)


def _inject_demo_anomalies(floor_states: list[FloorState]) -> None:
    """Randomly push 2-3 zones to warning/critical for demo visibility.

    Mutates zone states in place based on DEMO_ANOMALY_RATE.
    """
    all_zones = [z for f in floor_states for z in f.zones]
    if not all_zones:
        return

    target_count = random.randint(2, 3)
    candidates = [z for z in all_zones if z.status not in ("warning", "critical")]

    for zone in random.sample(candidates, min(target_count, len(candidates))):
        if random.random() > settings.DEMO_ANOMALY_RATE:
            continue
        # Pick a random anomaly type
        anomaly = random.choice(["co2", "temp_high", "temp_low"])
        if anomaly == "co2" and zone.co2_ppm is not None:
            zone.co2_ppm = random.uniform(1100, 1500)
            zone.status = "critical"
            zone.freedom_index = max(0, zone.freedom_index - 25)
        elif anomaly == "temp_high" and zone.temperature_c is not None:
            zone.temperature_c = random.uniform(27.5, 30.0)
            zone.status = "warning"
            zone.freedom_index = max(0, zone.freedom_index - 15)
        elif anomaly == "temp_low" and zone.temperature_c is not None:
            zone.temperature_c = random.uniform(14.0, 16.5)
            zone.status = "warning"
            zone.freedom_index = max(0, zone.freedom_index - 15)
    logger.debug("Demo mode: injected anomalies")
