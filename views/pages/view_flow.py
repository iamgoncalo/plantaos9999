"""Flow visualization page — zone-to-zone occupancy transitions as Sankey diagram."""

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


def create_flow_page() -> html.Div:
    """Create the Flow visualization page.

    Returns:
        Dash html.Div with Sankey diagram and controls.
    """
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:swap-horizontal", width=28, color=ACCENT_BLUE
                    ),
                    html.H2(
                        "Flow Analysis",
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
                "Zone-to-zone occupancy transitions over the selected time period.",
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
                        "Floor",
                        style={
                            "fontSize": "12px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    dcc.Dropdown(
                        id="flow-floor-select",
                        options=[
                            {"label": "All Floors", "value": "all"},
                            {"label": "Piso 0", "value": "0"},
                            {"label": "Piso 1", "value": "1"},
                        ],
                        value="all",
                        clearable=False,
                        style={"width": "160px"},
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px"},
            ),
            html.Div(
                [
                    html.Label(
                        "Time Range",
                        style={
                            "fontSize": "12px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    dcc.Dropdown(
                        id="flow-time-select",
                        options=[
                            {"label": "Last 24 Hours", "value": "24h"},
                            {"label": "Last 7 Days", "value": "7d"},
                            {"label": "Last 30 Days", "value": "30d"},
                        ],
                        value="24h",
                        clearable=False,
                        style={"width": "160px"},
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
                id="flow-sankey-graph",
                config={"displayModeBar": False},
                style={"height": "520px"},
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
