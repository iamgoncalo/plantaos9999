"""Smart Booking page — Room Finder + Analysis.

Primary mode: Find the best room for your needs (Booking.com-style).
Secondary mode: Analyze a specific room's historical or projected metrics.
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


def _label(text: str) -> html.Label:
    """Create a form label with consistent styling."""
    return html.Label(
        text,
        style={
            "fontSize": "13px",
            "fontWeight": 500,
            "color": TEXT_SECONDARY,
            "marginBottom": "6px",
            "display": "block",
        },
    )


def create_booking_page() -> html.Div:
    """Create the Smart Booking page layout.

    Returns:
        Dash html.Div containing the booking page with tabs
        for room finding and room analysis.
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
                "Find the best room for your needs, or analyze past and future bookings.",
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

    # ── Tab selector ──────────────────────────
    tab_selector = html.Div(
        dcc.RadioItems(
            id="booking-tab",
            options=[
                {"label": "Find Room", "value": "find"},
                {"label": "Analyze Room", "value": "analyze"},
            ],
            value="find",
            className="time-range-selector",
            inline=True,
        ),
        className="page-controls",
    )

    # ── Shared controls card ──────────────────
    shared_controls = html.Div(
        [
            html.Div(
                [
                    _label("Date"),
                    dcc.DatePickerSingle(
                        id="booking-date-picker",
                        display_format="YYYY-MM-DD",
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "140px"},
            ),
            html.Div(
                [
                    _label("Start Time"),
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
            html.Div(
                [
                    _label("Duration"),
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
            html.Div(
                [
                    _label("People"),
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

    # ══════════════════════════════════════════
    # FIND ROOM section
    # ══════════════════════════════════════════
    find_controls = html.Div(
        [
            html.Div(
                [
                    _label("Floor Preference"),
                    dcc.Dropdown(
                        id="booking-floor-pref",
                        options=[
                            {"label": "Any Floor", "value": "any"},
                            {"label": "Piso 0 (Ground)", "value": "0"},
                            {"label": "Piso 1 (First)", "value": "1"},
                        ],
                        value="any",
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "140px"},
            ),
            html.Div(
                [
                    _label("Requirements"),
                    dcc.Checklist(
                        id="booking-requirements",
                        options=[
                            {"label": " Projector", "value": "projector"},
                            {"label": " Computers", "value": "computers"},
                            {"label": " Quiet Zone", "value": "quiet"},
                        ],
                        value=[],
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "140px"},
            ),
            html.Button(
                [
                    DashIconify(icon="mdi:magnify", width=18, color="#FFFFFF"),
                    " Find Rooms",
                ],
                id="booking-find-btn",
                n_clicks=0,
                style={
                    "padding": "10px 28px",
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
                    "gap": "8px",
                    "transition": "all 300ms ease",
                    "alignSelf": "flex-end",
                },
            ),
        ],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-end",
        },
    )

    find_results = html.Div(
        id="booking-results-container",
        children=html.Div(
            [
                DashIconify(
                    icon="mdi:magnify",
                    width=32,
                    color=TEXT_TERTIARY,
                ),
                html.P(
                    "Select your requirements and click Find Rooms to see available options.",
                    style={
                        "color": TEXT_TERTIARY,
                        "fontSize": "13px",
                        "margin": "8px 0 0",
                    },
                ),
            ],
            style={
                "textAlign": "center",
                "padding": "40px 24px",
            },
        ),
    )

    find_calendar = html.Div(
        [
            html.H3(
                "Today's Bookings",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "margin": "0 0 12px",
                },
            ),
            dcc.Graph(
                id="booking-calendar-chart",
                config={
                    "displaylogo": False,
                    "displayModeBar": False,
                },
                style={"height": "200px"},
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

    find_section = html.Div(
        id="booking-find-section",
        children=[find_controls, find_results, find_calendar],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )

    # ══════════════════════════════════════════
    # ANALYZE ROOM section
    # ══════════════════════════════════════════
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    analyze_controls = html.Div(
        [
            html.Div(
                dcc.RadioItems(
                    id="booking-mode",
                    options=[
                        {"label": "Look Back", "value": "past"},
                        {"label": "Look Forward", "value": "future"},
                    ],
                    value="future",
                    className="time-range-selector",
                    inline=True,
                ),
                style={"flex": "0 0 auto"},
            ),
            html.Div(
                [
                    _label("Zone"),
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
            html.Button(
                [
                    DashIconify(icon="mdi:chart-line", width=18, color="#FFFFFF"),
                    " Analyze",
                ],
                id="booking-analyze-btn",
                n_clicks=0,
                style={
                    "padding": "10px 28px",
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
                    "gap": "8px",
                    "transition": "all 300ms ease",
                    "alignSelf": "flex-end",
                },
            ),
        ],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-end",
            "flexWrap": "wrap",
        },
    )

    analyze_results = html.Div(
        [
            html.Div(
                id="booking-kpi-grid",
                children=[create_kpi_skeleton() for _ in range(4)],
                className="grid-4",
            ),
            html.Div(
                dcc.Graph(
                    id="booking-physics-chart",
                    config={
                        "displaylogo": False,
                        "displayModeBar": "hover",
                        "modeBarButtonsToRemove": [
                            "lasso2d",
                            "select2d",
                        ],
                    },
                    style={"height": "360px"},
                ),
                className="chart-container",
            ),
        ],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "flexWrap": "wrap",
        },
    )

    analyze_recommendation = html.Div(
        id="booking-recommendation",
        children=html.Div(
            [
                DashIconify(
                    icon="mdi:information-outline",
                    width=20,
                    color=TEXT_TERTIARY,
                ),
                html.Span(
                    "Select a zone and click Analyze to get insights.",
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

    analyze_section = html.Div(
        id="booking-analyze-section",
        children=[analyze_controls, analyze_results, analyze_recommendation],
        style={
            "display": "none",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )

    # ── Confirm dialog + zone store ───────────
    confirm_dialog = dcc.ConfirmDialog(
        id="booking-confirm-dialog",
        message="Confirm this booking?",
    )
    confirm_store = dcc.Store(
        id="booking-confirm-zone-store",
        storage_type="memory",
    )
    booking_status = html.Div(id="booking-status-msg")

    return html.Div(
        [
            page_header,
            tab_selector,
            shared_controls,
            find_section,
            analyze_section,
            confirm_dialog,
            confirm_store,
            booking_status,
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )
