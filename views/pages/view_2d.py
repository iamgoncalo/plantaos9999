"""Standalone 2D floorplan view page with keyboard navigation.

Wraps the enhanced 2D floorplan renderer in a full-width layout
with metric and floor selector controls. Supports WASD/arrow-key
avatar movement with collision detection (Explore Mode).
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    TEXT_PRIMARY,
    TEXT_TERTIARY,
)
from core.geometry import FLOOR_0_WALKABLE


def create_view_2d_page() -> html.Div:
    """Create the standalone 2D floorplan page layout.

    Returns:
        Dash html.Div containing the 2D floorplan graph with metric
        and floor selector controls, plus avatar movement state.
    """
    # Header row with title and icon
    header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:map-outline",
                        width=24,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "2D Explore",
                        style={
                            "margin": "0 0 0 8px",
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
            ),
            html.Div(
                [
                    DashIconify(
                        icon="mdi:keyboard-outline", width=16, color=TEXT_TERTIARY
                    ),
                    html.Span(
                        "Use WASD or arrow keys to move avatar",
                        style={"fontSize": "12px", "color": TEXT_TERTIARY},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "6px"},
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": "16px",
        },
    )

    # Metric selector
    metric_selector = dcc.RadioItems(
        id="view2d-metric-selector",
        options=[
            {"label": "Zone Performance", "value": "freedom_index"},
            {"label": "Temperature", "value": "temperature_c"},
            {"label": "CO2", "value": "co2_ppm"},
            {"label": "Energy", "value": "total_energy_kwh"},
            {"label": "Operating Cost", "value": "financial_bleed"},
        ],
        value="freedom_index",
        className="time-range-selector",
        inline=True,
    )

    # Floor selector
    floor_selector = dcc.RadioItems(
        id="view2d-floor-selector",
        options=[
            {"label": "Piso 0", "value": "0"},
            {"label": "Piso 1", "value": "1"},
        ],
        value="0",
        className="time-range-selector",
        inline=True,
    )

    # Overlay toggle
    overlay_selector = dcc.RadioItems(
        id="view2d-overlay-selector",
        options=[
            {"label": "None", "value": "none"},
            {"label": "Heat", "value": "heat"},
            {"label": "Alerts", "value": "alerts"},
        ],
        value="none",
        className="time-range-selector",
        inline=True,
    )

    # Controls row
    controls = html.Div(
        [metric_selector, floor_selector, overlay_selector],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
            "marginBottom": "16px",
            "flexWrap": "wrap",
        },
    )

    # Stores for avatar, overlays, walkable polygons, and keyboard
    stores = html.Div(
        [
            dcc.Store(id="view2d-selected-zone", data=None),
            dcc.Store(id="view2d-keyboard-event", data=None),
            dcc.Store(id="view2d-avatar-pos", data={"x": 15.15, "y": 9.25}),
            dcc.Store(id="view2d-overlays", data=[]),
            dcc.Store(
                id="view2d-walkable-polys",
                data=FLOOR_0_WALKABLE,
            ),
            dcc.Interval(id="view2d-key-poll", interval=100, disabled=False),
        ]
    )

    # Full-width floorplan graph
    floorplan = dcc.Graph(
        id="view2d-floorplan-graph",
        config={"displayModeBar": False},
        style={"height": "520px"},
    )

    # Selected zone detail panel
    zone_detail = html.Div(
        id="view2d-zone-detail-panel",
        children=html.Div(
            [
                DashIconify(icon="mdi:cursor-pointer", width=20, color=TEXT_TERTIARY),
                html.Span(
                    "Click a zone or use WASD to explore",
                    style={"fontSize": "13px", "color": TEXT_TERTIARY},
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "8px",
                "padding": "16px 20px",
            },
        ),
        className="card",
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    return html.Div(
        [stores, header, controls, floorplan, zone_detail],
        className="page-enter",
        id="view2d-page-container",
        tabIndex="0",
        style={"outline": "none"},
    )
