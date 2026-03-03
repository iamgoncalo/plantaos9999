"""Zone polygon definitions for both floors.

Defines the 2D polygon coordinates for each zone, used by both
the 2D SVG renderer and the 3D view. Coordinates are in meters
relative to building origin (bottom-left corner of ground floor).

Geometry for the HORSE/Renault CFT training building in Aveiro.
Building bounding box: 30.3m x 18.3m per floor.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Floor dimensions in meters (building grid)
FLOOR_WIDTH_M = 30.3
FLOOR_HEIGHT_M = 18.3
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
# Ground Floor (Piso 0) — 30.3m x 18.3m grid
# =====================================================
_FLOOR_0_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South row (y=0 → 8.5) ──
    ZoneGeometry(
        id="p0_multiusos",
        name="Sala Multiusos",
        floor=0,
        points=[(0, 0), (11, 0), (11, 8.5), (0, 8.5)],
        area=93.10,
        capacity=60,
    ),
    ZoneGeometry(
        id="p0_biblioteca",
        name="Biblioteca/Espolio",
        floor=0,
        points=[(11, 0), (17, 0), (17, 8.5), (11, 8.5)],
        area=48.50,
        capacity=20,
    ),
    ZoneGeometry(
        id="p0_hall",
        name="Hall",
        floor=0,
        points=[(17, 0), (22.5, 0), (22.5, 8.5), (17, 8.5)],
        area=43.75,
        capacity=30,
    ),
    ZoneGeometry(
        id="p0_reuniao",
        name="Sala Reuniao",
        floor=0,
        points=[(22.5, 0), (26.5, 0), (26.5, 6), (22.5, 6)],
        area=25.10,
        capacity=12,
    ),
    ZoneGeometry(
        id="p0_recepcao",
        name="Recepcao",
        floor=0,
        points=[(26.5, 0), (30.3, 0), (30.3, 3), (26.5, 3)],
        area=10.15,
        capacity=5,
    ),
    ZoneGeometry(
        id="p0_arrumo",
        name="Arrumos",
        floor=0,
        points=[(26.5, 3), (30.3, 3), (30.3, 6), (26.5, 6)],
        area=8.00,
        capacity=0,
    ),
    ZoneGeometry(
        id="p0_wc",
        name="WCs",
        floor=0,
        points=[(22.5, 6), (30.3, 6), (30.3, 8.5), (22.5, 8.5)],
        area=24.00,
        capacity=0,
    ),
    # ── Corridor (y=8.5 → 10) ──
    ZoneGeometry(
        id="p0_circulacao",
        name="Circulacao",
        floor=0,
        points=[(0, 8.5), (30.3, 8.5), (30.3, 10), (0, 10)],
        area=50.30,
        capacity=0,
    ),
    # ── North row (y=10 → 18.3) ──
    ZoneGeometry(
        id="p0_auditorio",
        name="Auditorio",
        floor=0,
        points=[(0, 10), (9, 10), (9, 18.3), (0, 18.3)],
        area=72.70,
        capacity=57,
    ),
    ZoneGeometry(
        id="p0_sala",
        name="Sala Formacao",
        floor=0,
        points=[(9, 10), (15.2, 10), (15.2, 18.3), (9, 18.3)],
        area=51.00,
        capacity=30,
    ),
    ZoneGeometry(
        id="p0_copa",
        name="Zona Social / Copa",
        floor=0,
        points=[(15.2, 10), (19.5, 10), (19.5, 18.3), (15.2, 18.3)],
        area=35.15,
        capacity=15,
    ),
    ZoneGeometry(
        id="p0_informatica",
        name="Sala Informatica",
        floor=0,
        points=[(19.5, 10), (25.7, 10), (25.7, 18.3), (19.5, 18.3)],
        area=43.10,
        capacity=30,
    ),
]

# =====================================================
# First Floor (Piso 1) — 30.3m x 18.3m grid
# =====================================================
_FLOOR_1_ZONE_DEFS: list[ZoneGeometry] = [
    # ── South row (y=0 → 8.5) ──
    ZoneGeometry(
        id="p1_dojo",
        name="Sala Dojo Seguranca",
        floor=1,
        points=[(0, 0), (12.5, 0), (12.5, 8.5), (0, 8.5)],
        area=102.35,
        capacity=50,
    ),
    ZoneGeometry(
        id="p1_arquivo",
        name="Arquivo",
        floor=1,
        points=[(12.5, 0), (16, 0), (16, 8.5), (12.5, 8.5)],
        area=27.55,
        capacity=0,
    ),
    ZoneGeometry(
        id="p1_sala_a",
        name="Sala A",
        floor=1,
        points=[(16, 0), (24, 0), (24, 8.5), (16, 8.5)],
        area=63.15,
        capacity=35,
    ),
    ZoneGeometry(
        id="p1_reunioes",
        name="Sala Reunioes",
        floor=1,
        points=[(24, 0), (30.3, 0), (30.3, 5.5), (24, 5.5)],
        area=35.15,
        capacity=20,
    ),
    ZoneGeometry(
        id="p1_wc",
        name="WCs",
        floor=1,
        points=[(24, 5.5), (27, 5.5), (27, 8.5), (24, 8.5)],
        area=12.00,
        capacity=0,
    ),
    ZoneGeometry(
        id="p1_arrumos",
        name="Arrumos",
        floor=1,
        points=[(27, 5.5), (30.3, 5.5), (30.3, 8.5), (27, 8.5)],
        area=10.00,
        capacity=0,
    ),
    # ── Corridor (y=8.5 → 10) ──
    ZoneGeometry(
        id="p1_circulacao",
        name="Circulacao",
        floor=1,
        points=[(0, 8.5), (30.3, 8.5), (30.3, 10), (0, 10)],
        area=49.75,
        capacity=0,
    ),
    # ── North row (y=10 → 18.3) ──
    ZoneGeometry(
        id="p1_sala_b",
        name="Sala B",
        floor=1,
        points=[(0, 10), (7.5, 10), (7.5, 18.3), (0, 18.3)],
        area=51.00,
        capacity=30,
    ),
    ZoneGeometry(
        id="p1_sala_c",
        name="Sala C",
        floor=1,
        points=[(7.5, 10), (15, 10), (15, 18.3), (7.5, 18.3)],
        area=51.00,
        capacity=30,
    ),
    ZoneGeometry(
        id="p1_sala_d",
        name="Sala D",
        floor=1,
        points=[(15, 10), (22.5, 10), (22.5, 18.3), (15, 18.3)],
        area=51.00,
        capacity=30,
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
