"""Per-zone Freedom Index (health score 0-100).

Computes a composite health score for each zone based on comfort compliance,
energy efficiency, occupancy patterns, and anomaly rates.
Higher score = healthier zone.

Weights:
  - Comfort compliance: 40%
  - Energy efficiency: 30%
  - Occupancy health: 20%
  - Anomaly rate: 10%
"""

from __future__ import annotations


# Weight constants
WEIGHT_COMFORT = 0.40
WEIGHT_ENERGY = 0.30
WEIGHT_OCCUPANCY = 0.20
WEIGHT_ANOMALY = 0.10


def compute_zone_freedom(zone_id: str) -> float:
    """Compute the Freedom Index for a single zone.

    Args:
        zone_id: Zone to score.

    Returns:
        Score from 0.0 (poor) to 100.0 (excellent).
    """
    ...


def compute_building_freedom() -> dict[str, float]:
    """Compute Freedom Index for all zones in the building.

    Returns:
        Dict mapping zone_id to Freedom Index score.
    """
    ...


def _comfort_score(zone_id: str) -> float:
    """Score comfort compliance (0-100).

    Checks how well temperature, humidity, CO2, and lux stay within
    optimal bands.

    Args:
        zone_id: Zone identifier.

    Returns:
        Comfort subscore.
    """
    ...


def _energy_score(zone_id: str) -> float:
    """Score energy efficiency (0-100).

    Compares actual consumption to thresholds for the zone type,
    normalized by area.

    Args:
        zone_id: Zone identifier.

    Returns:
        Energy subscore.
    """
    ...


def _occupancy_score(zone_id: str) -> float:
    """Score occupancy health (0-100).

    Evaluates utilization rate, overcrowding incidents, and
    usage pattern regularity.

    Args:
        zone_id: Zone identifier.

    Returns:
        Occupancy subscore.
    """
    ...


def _anomaly_score(zone_id: str) -> float:
    """Score based on anomaly frequency (0-100).

    Lower anomaly rate = higher score.

    Args:
        zone_id: Zone identifier.

    Returns:
        Anomaly subscore.
    """
    ...
