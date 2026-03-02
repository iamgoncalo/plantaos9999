"""Plotly SVG floorplan renderer with zone overlays.

Generates an interactive 2D floorplan using Plotly shapes and
scatter traces, with zones colored by their Freedom Index or
selected comfort metric.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def render_floorplan_2d(
    floor: int = 0,
    zone_data: dict[str, float] | None = None,
    selected_zone: str | None = None,
    metric: str = "freedom_index",
) -> go.Figure:
    """Render a 2D floorplan with zone color overlays.

    Args:
        floor: Floor number to render (0 or 1).
        zone_data: Dict mapping zone_id to metric value for coloring.
        selected_zone: Zone to highlight with selection border.
        metric: Which metric the values represent.

    Returns:
        Plotly Figure with the floorplan.
    """
    ...


def _create_zone_shape(
    zone_id: str,
    polygon: list[tuple[float, float]],
    color: str,
    selected: bool = False,
) -> dict[str, Any]:
    """Create a Plotly shape dict for a single zone.

    Args:
        zone_id: Zone identifier.
        polygon: List of (x, y) polygon vertices.
        color: Fill color for the zone.
        selected: Whether to draw selection border.

    Returns:
        Plotly shape dictionary.
    """
    ...


def _create_zone_label(
    zone_id: str,
    name: str,
    center: tuple[float, float],
    value: float | None = None,
) -> go.Scatter:
    """Create a text label trace for a zone.

    Args:
        zone_id: Zone identifier.
        name: Display name.
        center: (x, y) center point for the label.
        value: Optional metric value to display.

    Returns:
        Plotly Scatter trace with text mode.
    """
    ...
