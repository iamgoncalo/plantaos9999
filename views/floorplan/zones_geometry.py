"""Zone polygon definitions for both floors.

Defines the 2D polygon coordinates for each zone, used by both
the 2D SVG renderer and the 3D view. Coordinates are in meters
relative to building origin (bottom-left corner of ground floor).

Geometry for the HORSE/Renault CFT training building in Aveiro.
Building bounding box: 30.30m x 18.30m per floor (from DWG).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Floor dimensions in meters (building grid — from DWG)
FLOOR_WIDTH_M = 30.30
FLOOR_HEIGHT_M = 18.30
FLOOR_HEIGHT_3D_M = 3.2  # Floor-to-ceiling height (Z offset for Piso 1)


class ZoneGeometry(BaseModel):
    """Geometry definition for a single building zone."""

    id: str = Field(description="Unique zone identifier matching config/building.py")
    name: str = Field(description="Human-readable zone name")
    floor: int = Field(description="Floor number (0 = ground, 1 = first)")
    points: list[tuple[float, float]] = Field(
        description="Polygon vertices as (x, y) tuples in meters"
    )
    area: float = Field(description="Zone area in square meters")
    capacity: int = Field(default=0, description="Maximum occupancy")


# =====================================================
# Ground Floor (Piso 0) — 30.30m x 18.30m grid (DWG)
# =====================================================
_FLOOR_0_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South band (y=0 → 7.40) ──
    ZoneGeometry(
        id="p0_multiusos",
        name="Sala Multiusos",
        floor=0,
        points=[(0, 0), (12.60, 0), (12.60, 7.40), (0, 7.40)],
        area=93.24,
        capacity=60,
    ),
    ZoneGeometry(
        id="p0_informatica",
        name="Sala Informatica",
        floor=0,
        points=[(12.60, 0), (18.40, 0), (18.40, 7.40), (12.60, 7.40)],
        area=42.92,
        capacity=59,
    ),
    ZoneGeometry(
        id="p0_reuniao",
        name="Sala Reuniao",
        floor=0,
        points=[(18.40, 0), (21.80, 0), (21.80, 7.40), (18.40, 7.40)],
        area=25.16,
        capacity=12,
    ),
    ZoneGeometry(
        id="p0_biblioteca",
        name="Biblioteca",
        floor=0,
        points=[(21.80, 0), (28.10, 0), (28.10, 7.40), (21.80, 7.40)],
        area=46.62,
        capacity=20,
    ),
    ZoneGeometry(
        id="p0_wc",
        name="WCs",
        floor=0,
        points=[(28.10, 0), (30.30, 0), (30.30, 7.40), (28.10, 7.40)],
        area=16.28,
        capacity=0,
    ),
    # ── Corridor (y=7.40 → 11.10) ──
    ZoneGeometry(
        id="p0_circulacao",
        name="Circulacao",
        floor=0,
        points=[(0, 7.40), (30.30, 7.40), (30.30, 11.10), (0, 11.10)],
        area=112.11,
        capacity=0,
    ),
    # ── North band (y=11.10 → 18.30) ──
    ZoneGeometry(
        id="p0_copa",
        name="Zona Social / Copa",
        floor=0,
        points=[(0, 11.10), (4.90, 11.10), (4.90, 18.30), (0, 18.30)],
        area=35.28,
        capacity=15,
    ),
    ZoneGeometry(
        id="p0_hall",
        name="Hall",
        floor=0,
        points=[(4.90, 11.10), (10.70, 11.10), (10.70, 18.30), (4.90, 18.30)],
        area=41.76,
        capacity=30,
    ),
    ZoneGeometry(
        id="p0_formacao1",
        name="Sala Formacao 1",
        floor=0,
        points=[(10.70, 11.10), (16.30, 11.10), (16.30, 18.30), (10.70, 18.30)],
        area=40.32,
        capacity=25,
    ),
    ZoneGeometry(
        id="p0_formacao2",
        name="Sala Formacao 2",
        floor=0,
        points=[(16.30, 11.10), (21.90, 11.10), (21.90, 18.30), (16.30, 18.30)],
        area=40.32,
        capacity=25,
    ),
    ZoneGeometry(
        id="p0_formacao3",
        name="Sala Formacao 3",
        floor=0,
        points=[(21.90, 11.10), (27.50, 11.10), (27.50, 18.30), (21.90, 18.30)],
        area=40.32,
        capacity=25,
    ),
]

# =====================================================
# First Floor (Piso 1) — 30.30m x 18.30m grid (DWG)
# =====================================================
_FLOOR_1_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South band (y=0 → 7.40) ──
    ZoneGeometry(
        id="p1_dojo",
        name="Sala Dojo Seguranca",
        floor=1,
        points=[(0, 0), (14.20, 0), (14.20, 7.40), (0, 7.40)],
        area=105.08,
        capacity=50,
    ),
    ZoneGeometry(
        id="p1_arquivo",
        name="Arquivo",
        floor=1,
        points=[(14.20, 0), (22.00, 0), (22.00, 7.40), (14.20, 7.40)],
        area=57.72,
        capacity=0,
    ),
    ZoneGeometry(
        id="p1_salagrande",
        name="Sala Grande",
        floor=1,
        points=[(22.00, 0), (27.80, 0), (27.80, 7.40), (22.00, 7.40)],
        area=42.92,
        capacity=25,
    ),
    ZoneGeometry(
        id="p1_salapequena",
        name="Sala Pequena",
        floor=1,
        points=[(27.80, 0), (30.30, 0), (30.30, 7.40), (27.80, 7.40)],
        area=18.50,
        capacity=15,
    ),
    # ── Corridor (y=7.40 → 11.10) ──
    ZoneGeometry(
        id="p1_circulacao",
        name="Circulacao",
        floor=1,
        points=[(0, 7.40), (30.30, 7.40), (30.30, 11.10), (0, 11.10)],
        area=112.11,
        capacity=0,
    ),
    # ── North band ──
    ZoneGeometry(
        id="p1_armazem",
        name="Exibicao Armazem",
        floor=1,
        points=[(0, 11.10), (3.60, 11.10), (3.60, 18.30), (0, 18.30)],
        area=25.92,
        capacity=0,
    ),
]

# Build lookup dicts keyed by zone_id -> polygon points (for backward compat)
FLOOR_0_ZONES: dict[str, list[tuple[float, float]]] = {
    z.id: z.points for z in _FLOOR_0_ZONE_DEFS
}
FLOOR_1_ZONES: dict[str, list[tuple[float, float]]] = {
    z.id: z.points for z in _FLOOR_1_ZONE_DEFS
}

# Combined lookup for all zone geometry models
_ALL_ZONE_GEOM: dict[str, ZoneGeometry] = {
    z.id: z for z in _FLOOR_0_ZONE_DEFS + _FLOOR_1_ZONE_DEFS
}


def get_zones_for_floor(floor: int) -> list[ZoneGeometry]:
    """Get all zone geometries for a specific floor.

    Args:
        floor: Floor number (0 or 1).

    Returns:
        List of ZoneGeometry models for the floor.
    """
    if floor == 0:
        return list(_FLOOR_0_ZONE_DEFS)
    if floor == 1:
        return list(_FLOOR_1_ZONE_DEFS)
    return []


def get_zone_geometry(zone_id: str) -> ZoneGeometry | None:
    """Get the geometry model for a specific zone.

    Args:
        zone_id: Zone identifier.

    Returns:
        ZoneGeometry model, or None if not found.
    """
    return _ALL_ZONE_GEOM.get(zone_id)


def get_zone_polygon(zone_id: str) -> list[tuple[float, float]]:
    """Get polygon coordinates for a zone.

    Args:
        zone_id: Zone identifier.

    Returns:
        List of (x, y) tuples, or empty list if not found.
    """
    if zone_id in FLOOR_0_ZONES:
        return FLOOR_0_ZONES[zone_id]
    if zone_id in FLOOR_1_ZONES:
        return FLOOR_1_ZONES[zone_id]
    return []


def get_zone_center(zone_id: str) -> tuple[float, float]:
    """Get the centroid of a zone polygon.

    Args:
        zone_id: Zone identifier.

    Returns:
        (x, y) center coordinates, or (0, 0) if not found.
    """
    polygon = get_zone_polygon(zone_id)
    if not polygon:
        return (0.0, 0.0)
    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]
    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
