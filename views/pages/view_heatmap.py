"""Heatmap visualization page — zone x hour matrix for selected metric."""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def create_heatmap_page() -> html.Div:
    """Create the Heatmap visualization page.

    Returns:
        Dash html.Div with heatmap chart and metric selector.
    """
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(icon="mdi:grid", width=28, color=ACCENT_BLUE),
                    html.H2(
                        "Heatmap View",
                        style={
                            "margin": 0,
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "12px"},
            ),
            html.P(
                "Zone performance across hours of the day.",
                style={
                    "margin": "8px 0 0",
                    "color": TEXT_SECONDARY,
                    "fontSize": "14px",
                },
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    controls = html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Metric",
                        style={
                            "fontSize": "12px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    dcc.Dropdown(
                        id="heatmap-metric-select",
                        options=[
                            {"label": "Temperature (°C)", "value": "temperature_c"},
                            {"label": "CO2 (ppm)", "value": "co2_ppm"},
                            {"label": "Humidity (%)", "value": "humidity_pct"},
                            {"label": "Occupancy", "value": "occupant_count"},
                            {"label": "Energy (kWh)", "value": "total_kwh"},
                        ],
                        value="temperature_c",
                        clearable=False,
                        style={"width": "200px"},
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px"},
            ),
            html.Div(
                [
                    html.Label(
                        "Floor",
                        style={
                            "fontSize": "12px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    dcc.Dropdown(
                        id="heatmap-floor-select",
                        options=[
                            {"label": "Piso 0", "value": 0},
                            {"label": "Piso 1", "value": 1},
                        ],
                        value=0,
                        clearable=False,
                        style={"width": "140px"},
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px"},
            ),
        ],
        style={"display": "flex", "gap": "16px", "marginBottom": f"{GAP_ELEMENT}px"},
    )

    chart_card = html.Div(
        [
            dcc.Graph(
                id="heatmap-chart",
                config={"displayModeBar": False},
                style={"height": "480px"},
            ),
        ],
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    return html.Div(
        [page_header, controls, chart_card],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": f"{GAP_ELEMENT}px"},
    )
