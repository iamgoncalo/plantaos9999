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

from config.building import get_zone_by_id, get_zones_by_floor
from config.settings import settings
from config.thresholds import evaluate_comfort
from core.freedom_index import compute_zone_freedom
from data.physical_ai_bridge import (
    edge_fusion_blend,
    get_current_physics_state,
    simulate_room_physics,
)
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
    # AFI fields
    perception: float = 0.0
    distortion: float = 1.0
    afi_freedom: float = 0.0
    financial_bleed_eur_hr: float = 0.0


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
    # AFI aggregate fields
    afi_state: dict | None = None
    total_financial_bleed_eur_hr: float = 0.0
    avg_afi_freedom: float = 0.0


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

    # ── Edge Fusion: blend sensor data with physics model ──
    try:
        zone_info = get_zone_by_id(zone_id)
        zone_area = zone_info.area_m2 if zone_info else 40.0
        has_sensor = zone_info.has_sensors if zone_info else False

        # Determine sensor confidence based on data freshness
        sensor_confidence = 0.0
        if comfort_df is not None and not comfort_df.empty:
            latest_ts = comfort_df["timestamp"].max()
            age_minutes = (now - latest_ts).total_seconds() / 60
            if age_minutes < 5:
                sensor_confidence = 0.9
            elif age_minutes < 30:
                sensor_confidence = 0.5
            elif age_minutes < 120:
                sensor_confidence = 0.1
        elif not has_sensor:
            sensor_confidence = 0.0

        # Run physics model for 1-step prediction
        if sensor_confidence < 0.9:
            physics_state = get_current_physics_state(zone_id)
            sim_states = simulate_room_physics(
                physics_state, zone_area, duration_minutes=5, step_minutes=5
            )
            if sim_states:
                sim_latest = sim_states[-1]
                if temp_c is not None:
                    temp_c = edge_fusion_blend(
                        sim_latest.temperature_c, temp_c, sensor_confidence
                    )
                else:
                    temp_c = sim_latest.temperature_c
                if co2 is not None:
                    co2 = edge_fusion_blend(sim_latest.co2_ppm, co2, sensor_confidence)
                else:
                    co2 = sim_latest.co2_ppm
    except Exception as exc:
        logger.debug(f"Edge fusion skipped for {zone_id}: {exc}")

    # Compute freedom index
    freedom = compute_zone_freedom(zone_id)

    # Compute AFI metrics (perception, distortion, financial bleed)
    afi_p, afi_d, afi_f, afi_bleed = 0.0, 1.0, 0.0, 0.0
    try:
        from core.afi_engine import (
            compute_financial_bleed,
            compute_freedom as afi_compute_freedom,
        )

        fr = afi_compute_freedom(zone_id)
        afi_p = fr.P
        afi_d = fr.D
        afi_f = fr.F
        bleed = compute_financial_bleed(zone_id)
        afi_bleed = bleed.total_bleed_eur_hr
    except Exception as exc:
        logger.debug(f"AFI computation skipped for {zone_id}: {exc}")

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
        perception=round(afi_p, 4),
        distortion=round(afi_d, 4),
        afi_freedom=round(afi_f, 4),
        financial_bleed_eur_hr=round(afi_bleed, 4),
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


_cached_state: BuildingState | None = None
_cached_version: int = -1


def compute_building_state() -> BuildingState:
    """Aggregate all floors into a building-wide state summary.

    Uses a cache keyed on store.version to skip recomputation when
    the underlying DataFrames haven't changed.

    Returns:
        BuildingState with building-level aggregated metrics.
    """
    global _cached_state, _cached_version  # noqa: PLW0603

    current_version = store.version
    if _cached_state is not None and _cached_version == current_version:
        logger.debug("Building state cache hit")
        return _cached_state

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

    # Compute AFI state (guarded so existing code doesn't break)
    afi_state_dict = None
    total_bleed = 0.0
    avg_afi_f = 0.0
    try:
        from core.afi_engine import compute_building_afi

        afi = compute_building_afi()
        afi_state_dict = afi.model_dump(mode="json")
        total_bleed = afi.total_financial_bleed_eur_hr
        avg_afi_f = afi.avg_freedom

        # Enrich zone states with AFI data
        for floor_state in floor_states:
            for zone_state in floor_state.zones:
                zone_afi = afi.zones.get(zone_state.zone_id)
                if zone_afi:
                    zone_state.perception = zone_afi.perception.P
                    zone_state.distortion = zone_afi.distortion.D
                    zone_state.afi_freedom = zone_afi.freedom.F
                    zone_state.financial_bleed_eur_hr = (
                        zone_afi.financial.total_bleed_eur_hr
                    )
    except Exception as e:
        logger.debug(f"AFI computation skipped: {e}")

    state = BuildingState(
        timestamp=now,
        floors=floor_states,
        total_occupancy=total_occ,
        total_energy_kwh=round(total_energy, 4),
        avg_freedom_index=round(avg_freedom, 1),
        active_alerts=active_alerts,
        afi_state=afi_state_dict,
        total_financial_bleed_eur_hr=round(total_bleed, 4),
        avg_afi_freedom=round(avg_afi_f, 4),
    )

    _cached_state = state
    _cached_version = current_version
    return state


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
    """Randomly push 2-3 zones to warning/critical for demo visibility.

    Mutates zone states in place based on DEMO_ANOMALY_RATE.

    Args:
        floor_states: Floor states to mutate in-place.
    """
    all_zones = [z for f in floor_states for z in f.zones]
    if not all_zones:
        return

    target_count = random.randint(2, 3)
    candidates = [z for z in all_zones if z.status not in ("warning", "critical")]

    for zone in random.sample(candidates, min(target_count, len(candidates))):
        if random.random() > settings.DEMO_ANOMALY_RATE:
            continue
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
