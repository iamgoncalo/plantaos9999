"""Smart Booking & Calendar page — The Temporal Oracle.

Users can look back at past events to see exact energy, comfort, and AFI
metrics, or look forward to simulate future bookings with projected
temperature, CO2, and cost estimates.
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
    FONT_STACK,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.kpi_card import create_kpi_skeleton


def create_booking_page() -> html.Div:
    """Create the Smart Booking page layout.

    Returns:
        Dash html.Div containing the booking page with mode toggle,
        controls, KPI grid, physics chart, and recommendation panel.
    """
    # ── Header ─────────────────────────────────
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:calendar-clock",
                        width=28,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "Smart Booking",
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
                "Temporal Intelligence Engine",
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

    # ── Mode Toggle ────────────────────────────
    mode_toggle = html.Div(
        dcc.RadioItems(
            id="booking-mode",
            options=[
                {"label": "Look Back", "value": "past"},
                {"label": "Look Forward", "value": "future"},
            ],
            value="past",
            className="time-range-selector",
            inline=True,
        ),
        className="page-controls",
    )

    # ── Controls Row ───────────────────────────
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    controls_row = html.Div(
        [
            # Zone selector
            html.Div(
                [
                    html.Label(
                        "Zone",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "6px",
                            "display": "block",
                        },
                    ),
                    dcc.Dropdown(
                        id="booking-zone-selector",
                        options=zone_options,
                        value=zone_options[0]["value"] if zone_options else None,
                        placeholder="Select a zone",
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "2", "minWidth": "160px"},
            ),
            # Date picker
            html.Div(
                [
                    html.Label(
                        "Date",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "6px",
                            "display": "block",
                        },
                    ),
                    dcc.DatePickerSingle(
                        id="booking-date-picker",
                        display_format="YYYY-MM-DD",
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "140px"},
            ),
            # Start hour
            html.Div(
                [
                    html.Label(
                        "Start Hour",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "6px",
                            "display": "block",
                        },
                    ),
                    dcc.Dropdown(
                        id="booking-time-start",
                        options=[
                            {"label": f"{h:02d}:00", "value": h} for h in range(6, 23)
                        ],
                        value=9,
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "100px"},
            ),
            # Duration
            html.Div(
                [
                    html.Label(
                        "Duration",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "6px",
                            "display": "block",
                        },
                    ),
                    dcc.Dropdown(
                        id="booking-duration",
                        options=[
                            {"label": "1h", "value": 1},
                            {"label": "2h", "value": 2},
                            {"label": "4h", "value": 4},
                            {"label": "8h", "value": 8},
                        ],
                        value=1,
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "90px"},
            ),
            # People count
            html.Div(
                [
                    html.Label(
                        "People",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "6px",
                            "display": "block",
                        },
                    ),
                    dcc.Input(
                        id="booking-people",
                        type="number",
                        min=1,
                        max=60,
                        value=15,
                        style={
                            "fontSize": "13px",
                            "width": "100%",
                            "padding": "8px 12px",
                            "border": "1px solid #E5E5EA",
                            "borderRadius": "8px",
                            "fontFamily": FONT_STACK,
                        },
                    ),
                ],
                style={"flex": "1", "minWidth": "90px"},
            ),
        ],
        className="card",
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-end",
            "flexWrap": "wrap",
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    # ── Analyze Button ─────────────────────────
    analyze_btn = html.Button(
        [
            DashIconify(icon="mdi:magnify", width=18, color="#FFFFFF"),
            " Analyze",
        ],
        id="booking-analyze-btn",
        n_clicks=0,
        style={
            "padding": "12px 32px",
            "background": ACCENT_BLUE,
            "color": "#FFFFFF",
            "border": "none",
            "borderRadius": "12px",
            "fontSize": "14px",
            "fontWeight": 600,
            "fontFamily": FONT_STACK,
            "cursor": "pointer",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "gap": "8px",
            "transition": "all 300ms ease",
        },
    )

    # ── Results: KPI Grid (left) ───────────────
    kpi_grid = html.Div(
        id="booking-kpi-grid",
        children=[create_kpi_skeleton() for _ in range(4)],
        className="grid-4",
        style={"flex": "1", "minWidth": 0},
    )

    # ── Results: Physics Chart (right) ─────────
    physics_chart = html.Div(
        dcc.Graph(
            id="booking-physics-chart",
            config={
                "displaylogo": False,
                "displayModeBar": "hover",
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
            style={"height": "360px"},
        ),
        className="chart-container",
        style={"flex": "1", "minWidth": 0},
    )

    # ── Results Two-Column ─────────────────────
    results_section = html.Div(
        [kpi_grid, physics_chart],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-start",
            "flexWrap": "wrap",
        },
    )

    # ── Recommendation Panel ───────────────────
    recommendation = html.Div(
        id="booking-recommendation",
        children=html.Div(
            [
                DashIconify(
                    icon="mdi:information-outline",
                    width=20,
                    color=TEXT_TERTIARY,
                ),
                html.Span(
                    "Select parameters and click Analyze to get a booking recommendation.",
                    style={"color": TEXT_TERTIARY, "fontSize": "13px"},
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
        [
            page_header,
            mode_toggle,
            controls_row,
            analyze_btn,
            results_section,
            recommendation,
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )
