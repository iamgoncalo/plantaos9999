"""Emergency Mode page: evacuation routes, fire response, and lockdown views.

Displays an interactive floorplan with emergency scenario overlays including
evacuation paths, danger zones, exit markers, and real-time status KPIs.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.building import get_monitored_zones
from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.kpi_card import create_kpi_skeleton


def create_emergency_page() -> html.Div:
    """Create the Emergency Mode page layout.

    Returns:
        Dash html.Div containing scenario selectors, floorplan,
        status KPIs, and recommendation panel.
    """
    # ── Header ─────────────────────────────────
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:fire-alert",
                        width=28,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "Emergency Mode",
                        style={
                            "margin": 0,
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                },
            ),
            html.P(
                "Visualize evacuation routes, danger zones, and emergency "
                "response scenarios across the building.",
                style={
                    "margin": "8px 0 0",
                    "color": TEXT_SECONDARY,
                    "fontSize": "14px",
                    "maxWidth": "640px",
                },
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # ── Scenario Selector ──────────────────────
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    scenario_selector = html.Div(
        [
            html.Label(
                "Scenario",
                style={
                    "fontSize": "13px",
                    "fontWeight": 500,
                    "color": TEXT_SECONDARY,
                    "marginBottom": "8px",
                    "display": "block",
                },
            ),
            dcc.Dropdown(
                id="emergency-scenario",
                options=[
                    {"label": "Fire", "value": "fire"},
                    {"label": "Smoke", "value": "smoke"},
                    {"label": "Evacuation", "value": "evacuation"},
                    {"label": "Lockdown", "value": "lockdown"},
                ],
                value="evacuation",
                clearable=False,
                style={"fontSize": "13px"},
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # ── Zone Origin Selector ───────────────────
    zone_origin_selector = html.Div(
        [
            html.Label(
                "Zone of Incident",
                style={
                    "fontSize": "13px",
                    "fontWeight": 500,
                    "color": TEXT_SECONDARY,
                    "marginBottom": "8px",
                    "display": "block",
                },
            ),
            dcc.Dropdown(
                id="emergency-zone-origin",
                options=zone_options,
                placeholder="Select zone of incident",
                clearable=True,
                style={"fontSize": "13px"},
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # ── Floor Selector ─────────────────────────
    floor_selector = html.Div(
        [
            html.Label(
                "Floor",
                style={
                    "fontSize": "13px",
                    "fontWeight": 500,
                    "color": TEXT_SECONDARY,
                    "marginBottom": "8px",
                    "display": "block",
                },
            ),
            dcc.RadioItems(
                id="emergency-floor-selector",
                options=[
                    {"label": "Piso 0", "value": "0"},
                    {"label": "Piso 1", "value": "1"},
                ],
                value="0",
                className="time-range-selector",
                inline=True,
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # ── Left Panel: Controls ───────────────────
    controls_panel = html.Div(
        [
            html.Div(
                "Emergency Configuration",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "marginBottom": "16px",
                },
            ),
            scenario_selector,
            zone_origin_selector,
            floor_selector,
        ],
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "minWidth": "280px",
        },
    )

    left_col = html.Div(
        controls_panel,
        style={
            "width": "320px",
            "flexShrink": 0,
            "position": "sticky",
            "top": "80px",
        },
    )

    # ── Right Panel: Floorplan + Status ────────
    floorplan_card = html.Div(
        dcc.Graph(
            id="emergency-floorplan",
            config={"displayModeBar": False},
            style={"height": "520px"},
        ),
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    status_panel = html.Div(
        id="emergency-status-panel",
        children=html.Div(
            [
                create_kpi_skeleton(),
                create_kpi_skeleton(),
                create_kpi_skeleton(),
                create_kpi_skeleton(),
            ],
            className="grid-4",
        ),
        style={"marginTop": f"{GAP_ELEMENT}px"},
    )

    recommendation_card = html.Div(
        id="emergency-recommendation",
        children=html.Div(
            [
                DashIconify(
                    icon="mdi:shield-alert-outline",
                    width=20,
                    color=TEXT_TERTIARY,
                ),
                html.Span(
                    "Select a scenario and zone of incident to view "
                    "emergency recommendations and evacuation routes.",
                    style={
                        "color": TEXT_TERTIARY,
                        "fontSize": "13px",
                    },
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
            "marginTop": f"{GAP_ELEMENT}px",
        },
    )

    right_panel = html.Div(
        [floorplan_card, status_panel, recommendation_card],
        style={"flex": "1", "minWidth": 0},
    )

    # ── Two-column layout ──────────────────────
    two_col = html.Div(
        [left_col, right_panel],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-start",
        },
    )

    return html.Div(
        [page_header, two_col],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )
