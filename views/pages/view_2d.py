"""Standalone 2D floorplan view page.

Wraps the enhanced 2D floorplan renderer in a full-width layout
with metric and floor selector controls.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import ACCENT_BLUE, TEXT_PRIMARY


def create_view_2d_page() -> html.Div:
    """Create the standalone 2D floorplan page layout.

    Returns:
        Dash html.Div containing the 2D floorplan graph with metric
        and floor selector controls.
    """
    # Header row with title and icon
    header = html.Div(
        [
            DashIconify(
                icon="mdi:map-outline",
                width=24,
                color=ACCENT_BLUE,
            ),
            html.H2(
                "2D Floorplan",
                style={
                    "margin": "0 0 0 8px",
                    "fontSize": "22px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                },
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "marginBottom": "16px",
        },
    )

    # Metric selector
    metric_selector = dcc.RadioItems(
        id="view2d-metric-selector",
        options=[
            {"label": "Building Health", "value": "freedom_index"},
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

    # Controls row
    controls = html.Div(
        [metric_selector, floor_selector],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
            "marginBottom": "16px",
            "flexWrap": "wrap",
        },
    )

    # Full-width floorplan graph
    floorplan = dcc.Graph(
        id="view2d-floorplan-graph",
        config={"displayModeBar": False},
        style={"height": "600px"},
    )

    return html.Div(
        [header, controls, floorplan],
        className="page-enter",
    )
