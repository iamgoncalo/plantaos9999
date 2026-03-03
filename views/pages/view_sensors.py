"""Sensor Coverage page for the PlantaOS digital twin.

Displays an interactive floorplan overlay showing sensor positions,
coverage radii, deployment status, and battery health across both
floors of the CFT building.
"""

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
    TEXT_TERTIARY,
)


def create_sensor_coverage_page() -> html.Div:
    """Create the Sensor Coverage page layout.

    Returns:
        Dash html.Div containing floor selector, coverage mode selector,
        an interactive floorplan graph, and a sensor catalog table.
    """
    # ── Page header ──────────────────────────────
    header = html.Div(
        [
            DashIconify(
                icon="mdi:access-point",
                width=28,
                color=ACCENT_BLUE,
            ),
            html.H2(
                "Sensor Coverage",
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
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    # ── Floor selector ───────────────────────────
    floor_selector = dcc.RadioItems(
        id="sensors-floor-selector",
        options=[
            {"label": "Piso 0", "value": "0"},
            {"label": "Piso 1", "value": "1"},
        ],
        value="0",
        className="time-range-selector",
        inline=True,
    )

    # ── Coverage mode selector ───────────────────
    mode_selector = dcc.RadioItems(
        id="sensors-coverage-mode",
        options=[
            {"label": "Coverage Map", "value": "coverage"},
            {"label": "Deployment Status", "value": "deployment"},
            {"label": "Battery Health", "value": "battery"},
        ],
        value="coverage",
        className="time-range-selector",
        inline=True,
    )

    # ── Controls row ─────────────────────────────
    controls = html.Div(
        [floor_selector, mode_selector],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
            "marginBottom": f"{GAP_ELEMENT}px",
            "flexWrap": "wrap",
        },
    )

    # ── Floorplan graph ──────────────────────────
    floorplan_card = html.Div(
        [
            dcc.Graph(
                id="sensors-coverage-graph",
                config={"displayModeBar": False},
                style={"height": "520px"},
            ),
        ],
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "padding": f"{PADDING_CARD}px",
        },
    )

    # ── Sensor catalog card ──────────────────────
    catalog_card = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:format-list-bulleted",
                        width=20,
                        color=ACCENT_BLUE,
                    ),
                    html.H3(
                        "Sensor Catalog",
                        style={
                            "margin": "0 0 0 8px",
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": f"{GAP_ELEMENT}px",
                },
            ),
            html.P(
                "Overview of sensor types deployed across the CFT building.",
                style={
                    "margin": "0 0 12px 0",
                    "fontSize": "13px",
                    "color": TEXT_SECONDARY,
                },
            ),
            html.Div(
                id="sensors-catalog-table",
                children=html.Span(
                    "Loading sensor catalog...",
                    style={
                        "fontSize": "13px",
                        "color": TEXT_TERTIARY,
                    },
                ),
            ),
        ],
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "padding": f"{PADDING_CARD}px",
            "marginTop": f"{GAP_ELEMENT}px",
        },
    )

    return html.Div(
        [header, controls, floorplan_card, catalog_card],
        className="page-enter",
    )
