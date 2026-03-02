"""Three.js HTML generator for 3D interactive building view.

Generates an HTML string containing a Three.js scene (r128) that
renders the CFT building in 3D with interactive zone selection
and metric overlays. Embedded via Dash html.Iframe.
"""

from __future__ import annotations


def generate_3d_html(
    building_data: dict | None = None,
    selected_zone: str | None = None,
) -> str:
    """Generate HTML/JS for the 3D building view.

    Args:
        building_data: Dict mapping zone_id to metric values for coloring.
        selected_zone: Zone to highlight.

    Returns:
        HTML string containing the Three.js scene.
    """
    ...


def _zone_to_mesh_params(
    zone_id: str,
    floor: int,
    polygon: list[tuple[float, float]],
    height: float = 3.0,
) -> dict:
    """Convert a zone polygon to Three.js mesh parameters.

    Args:
        zone_id: Zone identifier.
        floor: Floor number (affects vertical offset).
        polygon: 2D polygon vertices.
        height: Extrusion height in meters.

    Returns:
        Dict with position, geometry, and material parameters.
    """
    ...
