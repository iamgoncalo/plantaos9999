"""Zone state aggregation and spatial path computation.

Aggregates sensor readings into per-zone state summaries and computes
spatial relationships between zones for correlation analysis.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from pydantic import BaseModel, Field


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
    ...


def compute_floor_state(floor: int) -> FloorState:
    """Aggregate all zones on a floor into a floor state.

    Args:
        floor: Floor number (0 or 1).

    Returns:
        FloorState with aggregated metrics.
    """
    ...


def compute_building_state() -> BuildingState:
    """Aggregate all floors into a building-wide state summary.

    Returns:
        BuildingState with building-level aggregated metrics.
    """
    ...
