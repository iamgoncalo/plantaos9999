"""Plotly SVG floorplan renderer with zone overlays.

Generates an interactive 2D floorplan using Plotly shapes and
scatter traces, with zones colored by their Freedom Index or
selected comfort metric.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go

from config.building import get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    BORDER_DEFAULT,
    FONT_STACK,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
)
from utils.colors import hex_to_rgb, zone_health_to_color
from views.floorplan.zones_geometry import (
    FLOOR_0_ZONES,
    FLOOR_1_ZONES,
    FLOOR_HEIGHT_M,
    FLOOR_WIDTH_M,
    get_zone_center,
)

# Abbreviated names for compact zone labels
_NAME_SHORT: dict[str, str] = {
    "Sala Multiusos": "Multiusos",
    "Biblioteca / Espolio HORSE": "Biblioteca",
    "Zona Social / Copa": "Copa",
    "Sala Formacao 1": "Form. 1",
    "Sala Formacao 2": "Form. 2",
    "Sala Formacao 3": "Form. 3",
    "Sala Reuniao": "Reuniao",
    "Sala Informatica": "Informatica",
    "Exibicao Armazem": "Armazem",
    "Sala Dojo Seguranca": "Dojo",
    "Sala Grande": "Sala Grande",
    "Sala Pequena": "Sala Peq.",
}

# Team-color mapping: zone type → dot color for occupancy visualization
_ZONE_TEAM_COLORS: dict[str, str] = {
    "p0_informatica": "#5856D6",  # Engineering (purple)
    "p1_dojo": STATUS_CRITICAL,  # Safety (red)
    "p0_formacao1": STATUS_HEALTHY,  # Training (green)
    "p0_formacao2": STATUS_HEALTHY,
    "p0_formacao3": STATUS_HEALTHY,
    "p0_reuniao": "#5856D6",  # Management (purple)
    "p1_salagrande": "#5856D6",
    "p1_salapequena": "#5856D6",
}


def render_floorplan_2d(
    floor: int = 0,
    zone_data: dict[str, dict[str, Any]] | None = None,
    selected_zone: str | None = None,
    metric: str = "freedom_index",
) -> go.Figure:
    """Render a 2D floorplan with zone color overlays.

    Args:
        floor: Floor number to render (0 or 1).
        zone_data: Dict mapping zone_id to dict with metric values.
        selected_zone: Zone to highlight with selection border.
        metric: Which metric the values represent.

    Returns:
        Plotly Figure with the floorplan.
    """
    zones_geom = FLOOR_0_ZONES if floor == 0 else FLOOR_1_ZONES
    zone_data = zone_data or {}

    fig = go.Figure()
    shapes: list[dict] = []

    for zone_id, polygon in zones_geom.items():
        zd = zone_data.get(zone_id, {})

        # Handle both dict and float zone_data values
        if isinstance(zd, dict):
            score = zd.get("freedom_index", 50.0)
            occ = zd.get("occupant_count", 0)
            bleed = zd.get("financial_bleed", 0) or zd.get("financial_bleed_eur_hr", 0)
        else:
            score = float(zd)
            occ = 0
            bleed = 0

        color = zone_health_to_color(score)
        is_selected = zone_id == selected_zone

        # Zone shape
        shapes.append(_create_zone_shape(zone_id, polygon, color, is_selected))

        # Zone label (with €/hr if available)
        zone_info = get_zone_by_id(zone_id)
        name = zone_info.name if zone_info else zone_id
        center = get_zone_center(zone_id)
        fig.add_trace(
            _create_zone_label(zone_id, name, center, occ if occ else None, bleed)
        )

        # Hover trace (invisible marker with rich tooltip)
        fig.add_trace(_create_hover_trace(zone_id, center, zd, zone_info))

        # Occupancy dots (team-colored)
        if occ and occ > 0:
            dot_color = _ZONE_TEAM_COLORS.get(zone_id, ACCENT_BLUE)
            dots = _create_occupancy_dots(zone_id, polygon, occ, dot_color)
            if dots is not None:
                fig.add_trace(dots)

    # Color legend
    fig.add_trace(_create_color_legend())

    fig.update_layout(
        shapes=shapes,
        xaxis=dict(
            range=[-1, FLOOR_WIDTH_M + 1],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=True,
        ),
        yaxis=dict(
            range=[-1, FLOOR_HEIGHT_M + 1],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BG_CARD,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        height=500,
        dragmode=False,
        hoverlabel=dict(
            bgcolor=BG_CARD,
            bordercolor=BORDER_DEFAULT,
            font=dict(family=FONT_STACK, size=12),
        ),
    )

    return fig


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
    path_parts = [f"M {polygon[0][0]} {polygon[0][1]}"]
    for x, y in polygon[1:]:
        path_parts.append(f"L {x} {y}")
    path_parts.append("Z")
    path_str = " ".join(path_parts)

    r, g, b = hex_to_rgb(color)
    opacity = 0.6 if selected else 0.35
    fill_color = f"rgba({r}, {g}, {b}, {opacity})"

    return {
        "type": "path",
        "path": path_str,
        "fillcolor": fill_color,
        "line": {
            "color": ACCENT_BLUE if selected else BORDER_DEFAULT,
            "width": 2.5 if selected else 1,
        },
        "layer": "below",
        "name": zone_id,
    }


def _create_zone_label(
    zone_id: str,
    name: str,
    center: tuple[float, float],
    value: float | None = None,
    bleed_eur_hr: float = 0,
) -> go.Scatter:
    """Create a text label trace for a zone.

    Args:
        zone_id: Zone identifier.
        name: Display name.
        center: (x, y) center point for the label.
        value: Optional metric value to display.
        bleed_eur_hr: Financial bleed in €/hr to display below name.

    Returns:
        Plotly Scatter trace with text mode.
    """
    short_name = _NAME_SHORT.get(name, name)
    parts = [f"<b>{short_name}</b>"]
    if value is not None:
        parts.append(str(int(value)))
    if bleed_eur_hr and bleed_eur_hr > 0.01:
        parts.append(
            f"<span style='color:{STATUS_WARNING}'>€{bleed_eur_hr:.2f}/hr</span>"
        )

    text = "<br>".join(parts)

    return go.Scatter(
        x=[center[0]],
        y=[center[1]],
        mode="text",
        text=[text],
        textfont=dict(family=FONT_STACK, size=9, color=TEXT_PRIMARY),
        hoverinfo="skip",
        showlegend=False,
        customdata=[zone_id],
    )


def _create_hover_trace(
    zone_id: str,
    center: tuple[float, float],
    zone_data: dict[str, Any],
    zone_info: Any,
) -> go.Scatter:
    """Create an invisible hover trace for a zone.

    Args:
        zone_id: Zone identifier.
        center: (x, y) center point.
        zone_data: Metric values dict.
        zone_info: Zone model from building config.

    Returns:
        Plotly Scatter trace with hover tooltip.
    """
    name = zone_info.name if zone_info else zone_id

    if isinstance(zone_data, dict) and zone_data:
        temp = zone_data.get("temperature_c")
        hum = zone_data.get("humidity_pct")
        co2 = zone_data.get("co2_ppm")
        occ = zone_data.get("occupant_count", 0)
        energy = zone_data.get("total_energy_kwh", 0)
        freedom = zone_data.get("freedom_index", 0)
        cap = zone_info.capacity if zone_info else 0

        lines = [f"<b>{name}</b>"]
        if temp is not None:
            lines.append(f"Temperature: {temp:.1f} °C")
        if hum is not None:
            lines.append(f"Humidity: {hum:.0f}%")
        if co2 is not None:
            lines.append(f"CO2: {co2:.0f} ppm")
        lines.append(f"Occupancy: {occ}/{cap}")
        lines.append(f"Energy: {energy:.2f} kWh")
        lines.append(f"Freedom Index: {freedom:.0f}/100")
        bleed_val = zone_data.get("financial_bleed", 0) or zone_data.get(
            "financial_bleed_eur_hr", 0
        )
        if bleed_val:
            lines.append(f"Financial Bleed: €{bleed_val:.2f}/hr")
        hover_text = "<br>".join(lines)
    else:
        hover_text = f"<b>{name}</b><br>No data available"

    return go.Scatter(
        x=[center[0]],
        y=[center[1]],
        mode="markers",
        marker=dict(size=25, opacity=0),
        hovertext=[hover_text],
        hoverinfo="text",
        showlegend=False,
        customdata=[zone_id],
    )


def _create_occupancy_dots(
    zone_id: str,
    polygon: list[tuple[float, float]],
    count: int,
    dot_color: str = ACCENT_BLUE,
) -> go.Scatter | None:
    """Generate occupancy dots inside a zone polygon.

    Args:
        zone_id: Zone identifier (used for stable RNG seed).
        polygon: Zone polygon vertices.
        count: Number of occupants.
        dot_color: Color for the dots (team-based coloring).

    Returns:
        Plotly Scatter trace with dot markers, or None if no dots.
    """
    n_dots = min(count, 15)
    if n_dots <= 0:
        return None

    # Stable RNG seeded from zone_id
    seed = hash(zone_id) % (2**31)
    rng = np.random.default_rng(seed)

    # Bounding box
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Shrink bounds slightly to keep dots away from edges
    pad = 0.5
    x_min += pad
    x_max -= pad
    y_min += pad
    y_max -= pad

    if x_max <= x_min or y_max <= y_min:
        return None

    # Generate points inside polygon
    dot_x: list[float] = []
    dot_y: list[float] = []
    attempts = 0
    while len(dot_x) < n_dots and attempts < n_dots * 10:
        x = rng.uniform(x_min, x_max)
        y = rng.uniform(y_min, y_max)
        if _point_in_polygon(x, y, polygon):
            dot_x.append(x)
            dot_y.append(y)
        attempts += 1

    if not dot_x:
        return None

    return go.Scatter(
        x=dot_x,
        y=dot_y,
        mode="markers",
        marker=dict(
            size=5,
            color=dot_color,
            opacity=0.5,
        ),
        hoverinfo="skip",
        showlegend=False,
    )


def _create_color_legend() -> go.Scatter:
    """Create a color legend trace for the freedom index scale.

    Returns:
        Plotly Scatter trace with colorbar.
    """
    return go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker=dict(
            size=0,
            colorscale=[
                [0.0, STATUS_CRITICAL],
                [0.3, STATUS_WARNING],
                [0.5, "#FFD60A"],
                [0.8, STATUS_HEALTHY],
                [1.0, STATUS_HEALTHY],
            ],
            cmin=0,
            cmax=100,
            colorbar=dict(
                title=dict(text="Freedom Index", font=dict(size=11)),
                thickness=12,
                len=0.5,
                x=1.02,
                y=0.5,
                tickvals=[0, 25, 50, 75, 100],
                tickfont=dict(size=10),
                outlinewidth=0,
            ),
            showscale=True,
        ),
        showlegend=False,
        hoverinfo="skip",
    )


def _point_in_polygon(
    x: float,
    y: float,
    polygon: list[tuple[float, float]],
) -> bool:
    """Ray-casting point-in-polygon test.

    Args:
        x: X coordinate.
        y: Y coordinate.
        polygon: List of (x, y) vertices.

    Returns:
        True if point is inside the polygon.
    """
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
