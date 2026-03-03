"""Floor geometry source-of-truth with wall polygons for collision detection.

The CFT building is 30.30m x 18.30m with a 3-band layout:
- South band: y=0 to y=7.40  (rooms)
- Corridor:   y=7.40 to y=11.10 (3.70m wide)
- North band: y=11.10 to y=18.30 (rooms)
"""

from __future__ import annotations


BUILDING_WIDTH_M: float = 30.30
BUILDING_HEIGHT_M: float = 18.30
BAND_SOUTH_TOP: float = 7.40
CORRIDOR_TOP: float = 11.10
BAND_NORTH_TOP: float = 18.30

# Zone polygons for collision — each is [(x1,y1), (x2,y2), ...]
# Walkable = inside any zone OR inside corridor
FLOOR_0_WALKABLE: list[list[tuple[float, float]]] = [
    # Bottom band zones
    [(0, 0), (12.60, 0), (12.60, 7.40), (0, 7.40)],  # multiusos
    [(12.60, 0), (18.40, 0), (18.40, 7.40), (12.60, 7.40)],  # informatica
    [(18.40, 0), (21.80, 0), (21.80, 7.40), (18.40, 7.40)],  # reuniao
    [(21.80, 0), (28.10, 0), (28.10, 7.40), (21.80, 7.40)],  # biblioteca
    [(28.10, 0), (30.30, 0), (30.30, 7.40), (28.10, 7.40)],  # wc
    # Corridor
    [(0, 7.40), (30.30, 7.40), (30.30, 11.10), (0, 11.10)],
    # Top band zones
    [(0, 11.10), (4.90, 11.10), (4.90, 18.30), (0, 18.30)],
    [(4.90, 11.10), (10.70, 11.10), (10.70, 18.30), (4.90, 18.30)],
    [(10.70, 11.10), (16.30, 11.10), (16.30, 18.30), (10.70, 18.30)],
    [(16.30, 11.10), (21.90, 11.10), (21.90, 18.30), (16.30, 18.30)],
    [(21.90, 11.10), (27.50, 11.10), (27.50, 18.30), (21.90, 18.30)],
]

FLOOR_1_WALKABLE: list[list[tuple[float, float]]] = [
    [(0, 0), (14.20, 0), (14.20, 7.40), (0, 7.40)],
    [(14.20, 0), (22.00, 0), (22.00, 7.40), (14.20, 7.40)],
    [(22.00, 0), (27.80, 0), (27.80, 7.40), (22.00, 7.40)],
    [(27.80, 0), (30.30, 0), (30.30, 7.40), (27.80, 7.40)],
    [(0, 7.40), (30.30, 7.40), (30.30, 11.10), (0, 11.10)],
    [(0, 11.10), (3.60, 11.10), (3.60, 18.30), (0, 18.30)],
]


def point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_building(x: float, y: float, floor: int = 0) -> bool:
    """Check if point is inside any walkable polygon on the given floor."""
    polys = FLOOR_0_WALKABLE if floor == 0 else FLOOR_1_WALKABLE
    return any(point_in_polygon(x, y, poly) for poly in polys)


def get_walkable_polygons(floor: int = 0) -> list[list[tuple[float, float]]]:
    """Return walkable polygons for the given floor."""
    return FLOOR_0_WALKABLE if floor == 0 else FLOOR_1_WALKABLE
