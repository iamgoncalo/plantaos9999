"""Zone polygon definitions for both floors.

Defines the 2D polygon coordinates for each zone, used by both
the 2D SVG renderer and the 3D view. Coordinates are in meters
relative to building origin (bottom-left corner of ground floor).
"""

from __future__ import annotations

# Floor dimensions in meters (approximate)
FLOOR_WIDTH_M = 35.0
FLOOR_HEIGHT_M = 25.0
FLOOR_HEIGHT_3D_M = 3.2  # Floor-to-ceiling height

# ═══════════════════════════════════════════════
# Ground Floor (Piso 0) — Zone Polygons
# ═══════════════════════════════════════════════
# Coordinates: list of (x, y) tuples in meters
# Placeholder geometry — to be replaced with actual CAD data
FLOOR_0_ZONES: dict[str, list[tuple[float, float]]] = {
    "p0_sala_multiusos": [(0, 0), (12, 0), (12, 8), (0, 8)],
    "p0_biblioteca": [(12, 0), (19, 0), (19, 7), (12, 7)],
    "p0_zona_social": [(19, 0), (25, 0), (25, 6), (19, 6)],
    "p0_hall": [(0, 8), (7, 8), (7, 14), (0, 14)],
    "p0_circulacao": [(7, 8), (25, 8), (25, 10), (7, 10)],
    "p0_aula_camara": [(25, 0), (29, 0), (29, 5), (25, 5)],
    "p0_formacao_1": [(0, 14), (8, 14), (8, 21), (0, 21)],
    "p0_formacao_2": [(8, 14), (15, 14), (15, 20), (8, 20)],
    "p0_formacao_3": [(15, 14), (21, 14), (21, 19), (15, 19)],
    "p0_reuniao": [(21, 14), (26, 14), (26, 19), (21, 19)],
    "p0_informatica": [(26, 10), (33, 10), (33, 16), (26, 16)],
    "p0_auditorio": [(26, 16), (33, 16), (33, 22), (26, 22)],
    "p0_arrumos": [(0, 21), (4, 21), (4, 24), (0, 24)],
    "p0_recepcao": [(4, 21), (9, 21), (9, 24), (4, 24)],
    "p0_wc_m": [(9, 21), (13, 21), (13, 24), (9, 24)],
    "p0_wc_f": [(13, 21), (17, 21), (17, 24), (13, 24)],
}

# ═══════════════════════════════════════════════
# First Floor (Piso 1) — Zone Polygons
# ═══════════════════════════════════════════════
FLOOR_1_ZONES: dict[str, list[tuple[float, float]]] = {
    "p1_arquivo": [(0, 0), (9, 0), (9, 7), (0, 7)],
    "p1_sala_grande": [(9, 0), (16, 0), (16, 6), (9, 6)],
    "p1_sala_pequena": [(16, 0), (21, 0), (21, 5), (16, 5)],
    "p1_sala_1": [(0, 7), (7, 7), (7, 14), (0, 14)],
    "p1_sala_2": [(7, 7), (13, 7), (13, 13), (7, 13)],
    "p1_sala_3": [(13, 7), (18, 7), (18, 13), (13, 13)],
    "p1_circulacao": [(18, 5), (25, 5), (25, 8), (18, 8)],
    "p1_producao": [(21, 0), (26, 0), (26, 5), (21, 5)],
    "p1_dojo": [(18, 8), (33, 8), (33, 18), (18, 18)],
    "p1_wc": [(0, 14), (4, 14), (4, 17), (0, 17)],
    "p1_monitor": [(4, 14), (8, 14), (8, 18), (4, 18)],
}


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
