"""Canonical BuildingState producer -- combines fused data for all zones.

Provides a single entry point to query the current smoothed state
of any zone or the entire building. Delegates to core.fuse for
per-zone EMA values and config.building for the zone registry.
"""

from __future__ import annotations

from config.building import get_monitored_zones, get_zone_by_id
from core.fuse import get_fused_state


def get_canonical_zone_state(zone_id: str) -> dict[str, float]:
    """Get the current fused metric state for a single zone.

    Args:
        zone_id: Building zone identifier.

    Returns:
        Dict of metric_name -> smoothed value.
    """
    return get_fused_state(zone_id)


def get_all_zone_states() -> dict[str, dict[str, float]]:
    """Get fused metric state for all monitored zones.

    Returns:
        Dict mapping zone_id to its fused metric dict.
    """
    return {z.id: get_fused_state(z.id) for z in get_monitored_zones()}


def get_zone_summary(zone_id: str) -> dict:
    """Get a summary combining zone metadata and live state.

    Args:
        zone_id: Building zone identifier.

    Returns:
        Dict with zone info plus current fused metrics.
    """
    zone = get_zone_by_id(zone_id)
    state = get_fused_state(zone_id)
    if zone is None:
        return {"zone_id": zone_id, "metrics": state}
    return {
        "zone_id": zone_id,
        "name": zone.name,
        "floor": zone.floor,
        "area_m2": zone.area_m2,
        "capacity": zone.capacity,
        "zone_type": zone.zone_type.value,
        "metrics": state,
    }


def get_building_snapshot() -> list[dict]:
    """Get a snapshot of all monitored zones with metadata.

    Returns:
        List of zone summary dicts.
    """
    return [get_zone_summary(z.id) for z in get_monitored_zones()]
