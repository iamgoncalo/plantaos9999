"""Zone polygon definitions for both floors.

Defines the 2D polygon coordinates for each zone, used by both
the 2D SVG renderer and the 3D view. Coordinates are in meters
relative to building origin (bottom-left corner of ground floor).

Geometry for the HORSE/Renault CFT training building in Aveiro.
Building bounding box: 48.4m x 15.0m per floor (from DWG).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Floor dimensions in meters (building grid — from DWG)
FLOOR_WIDTH_M = 48.4
FLOOR_HEIGHT_M = 15.0
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
# Ground Floor (Piso 0) — 48.4m x 15.0m grid (DWG)
# =====================================================
_FLOOR_0_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South row (y=0 → 9.3) ──
    ZoneGeometry(
        id="p0_multiusos",
        name="Sala Multiusos",
        floor=0,
        points=[(0, 0), (10, 0), (10, 9.3), (0, 9.3)],
        area=93.0,
        capacity=60,
    ),
    ZoneGeometry(
        id="p0_biblioteca",
        name="Biblioteca",
        floor=0,
        points=[(10, 0), (15, 0), (15, 9.3), (10, 9.3)],
        area=46.5,
        capacity=20,
    ),
    ZoneGeometry(
        id="p0_copa",
        name="Zona Social / Copa",
        floor=0,
        points=[(15, 0), (22, 0), (22, 5), (15, 5)],
        area=35.0,
        capacity=15,
    ),
    ZoneGeometry(
        id="p0_hall",
        name="Hall",
        floor=0,
        points=[(22, 0), (30, 0), (30, 5), (22, 5)],
        area=40.0,
        capacity=30,
    ),
    # ── Corridor (y=9.3 → 11) ──
    ZoneGeometry(
        id="p0_circulacao",
        name="Circulacao",
        floor=0,
        points=[(0, 9.3), (30, 9.3), (30, 11), (0, 11)],
        area=51.0,
        capacity=0,
    ),
    # ── East rooms (x=30 → 48.4, y=0 → 5) ──
    ZoneGeometry(
        id="p0_reuniao",
        name="Sala Reuniao",
        floor=0,
        points=[(30, 0), (35, 0), (35, 5), (30, 5)],
        area=25.0,
        capacity=12,
    ),
    ZoneGeometry(
        id="p0_informatica",
        name="Sala Informatica",
        floor=0,
        points=[(35, 0), (43.3, 0), (43.3, 5), (35, 5)],
        area=41.5,
        capacity=59,
    ),
    # ── North row (y=11 → 15) ──
    ZoneGeometry(
        id="p0_formacao1",
        name="Sala Formacao 1",
        floor=0,
        points=[(0, 11), (10, 11), (10, 15), (0, 15)],
        area=40.0,
        capacity=25,
    ),
    ZoneGeometry(
        id="p0_formacao2",
        name="Sala Formacao 2",
        floor=0,
        points=[(10, 11), (20, 11), (20, 15), (10, 15)],
        area=40.0,
        capacity=25,
    ),
    ZoneGeometry(
        id="p0_formacao3",
        name="Sala Formacao 3",
        floor=0,
        points=[(20, 11), (30, 11), (30, 15), (20, 15)],
        area=40.0,
        capacity=25,
    ),
    # ── Sanitary (far east) ──
    ZoneGeometry(
        id="p0_wc",
        name="WCs",
        floor=0,
        points=[(43.3, 0), (48.4, 0), (48.4, 5), (43.3, 5)],
        area=25.5,
        capacity=0,
    ),
]

# =====================================================
# First Floor (Piso 1) — 48.4m x 15.0m grid (DWG)
# =====================================================
_FLOOR_1_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South row (y=0 → 7.3) ──
    ZoneGeometry(
        id="p1_dojo",
        name="Sala Dojo Seguranca",
        floor=1,
        points=[(0, 0), (15, 0), (15, 7.3), (0, 7.3)],
        area=109.5,
        capacity=50,
    ),
    ZoneGeometry(
        id="p1_arquivo",
        name="Arquivo",
        floor=1,
        points=[(15, 0), (22.8, 0), (22.8, 7.3), (15, 7.3)],
        area=56.9,
        capacity=0,
    ),
    ZoneGeometry(
        id="p1_salagrande",
        name="Sala Grande",
        floor=1,
        points=[(22.8, 0), (30, 0), (30, 5.8), (22.8, 5.8)],
        area=41.8,
        capacity=25,
    ),
    ZoneGeometry(
        id="p1_salapequena",
        name="Sala Pequena",
        floor=1,
        points=[(30, 0), (35, 0), (35, 5), (30, 5)],
        area=25.0,
        capacity=15,
    ),
    # ── Corridor (y=7.3 → 9) ──
    ZoneGeometry(
        id="p1_circulacao",
        name="Circulacao",
        floor=1,
        points=[(0, 7.3), (30, 7.3), (30, 9), (0, 9)],
        area=51.0,
        capacity=0,
    ),
    # ── East production area ──
    ZoneGeometry(
        id="p1_armazem",
        name="Exibicao Armazem",
        floor=1,
        points=[(35, 0), (40.1, 0), (40.1, 5), (35, 5)],
        area=25.5,
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
