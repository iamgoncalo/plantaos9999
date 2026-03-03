"""What-if simulation page: scenario testing and impact analysis.

Allows users to trigger catastrophic and operational scenarios (fire,
open window, mass entry, HVAC failure) on any building zone and
visualize the projected cascade effects, timeline, and financial damage.
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
    STATUS_CRITICAL,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.charts import chart_card
from views.components.kpi_card import create_kpi_card


def create_simulation_page() -> html.Div:
    """Create the what-if simulation page layout.

    Returns:
        Dash html.Div containing the simulation page with event
        trigger panel, timeline chart, and damage summary.
    """
    # ── Header ─────────────────────────────────
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:play-circle-outline",
                        width=28,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "What-If Simulation",
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
                "Test catastrophic and operational scenarios to predict "
                "cascade effects, evacuation times, and financial impact.",
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

    # ── Hidden store for simulation results ────
    result_store = dcc.Store(id="sim-result-store", storage_type="memory")

    # ── Left panel: Event trigger ──────────────
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    event_trigger_panel = html.Div(
        [
            html.Div(
                "Scenario Configuration",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "marginBottom": "16px",
                },
            ),
            # Event type selector
            html.Div(
                [
                    html.Label(
                        "Event Type",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "8px",
                            "display": "block",
                        },
                    ),
                    dcc.RadioItems(
                        id="sim-event-type",
                        options=[
                            {
                                "label": html.Span(
                                    [
                                        DashIconify(
                                            icon="mdi:fire",
                                            width=16,
                                            color=STATUS_CRITICAL,
                                        ),
                                        " Fire",
                                    ],
                                    style={
                                        "display": "inline-flex",
                                        "alignItems": "center",
                                        "gap": "4px",
                                    },
                                ),
                                "value": "fire",
                            },
                            {
                                "label": html.Span(
                                    [
                                        DashIconify(
                                            icon="mdi:window-open-variant",
                                            width=16,
                                            color=STATUS_WARNING,
                                        ),
                                        " Open Window",
                                    ],
                                    style={
                                        "display": "inline-flex",
                                        "alignItems": "center",
                                        "gap": "4px",
                                    },
                                ),
                                "value": "open_window",
                            },
                            {
                                "label": html.Span(
                                    [
                                        DashIconify(
                                            icon="mdi:account-group",
                                            width=16,
                                            color=ACCENT_BLUE,
                                        ),
                                        " Mass Entry",
                                    ],
                                    style={
                                        "display": "inline-flex",
                                        "alignItems": "center",
                                        "gap": "4px",
                                    },
                                ),
                                "value": "mass_entry",
                            },
                            {
                                "label": html.Span(
                                    [
                                        DashIconify(
                                            icon="mdi:air-conditioner",
                                            width=16,
                                            color=TEXT_TERTIARY,
                                        ),
                                        " HVAC Failure",
                                    ],
                                    style={
                                        "display": "inline-flex",
                                        "alignItems": "center",
                                        "gap": "4px",
                                    },
                                ),
                                "value": "hvac_failure",
                            },
                        ],
                        value="fire",
                        className="sim-radio-group",
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "gap": "10px",
                        },
                    ),
                ],
                style={"marginBottom": "20px"},
            ),
            # Zone selector
            html.Div(
                [
                    html.Label(
                        "Target Zone",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "8px",
                            "display": "block",
                        },
                    ),
                    dcc.Dropdown(
                        id="sim-zone-selector",
                        options=zone_options,
                        value=zone_options[0]["value"] if zone_options else None,
                        placeholder="Select a zone",
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                style={"marginBottom": "20px"},
            ),
            # Intensity slider
            html.Div(
                [
                    html.Label(
                        "Intensity",
                        style={
                            "fontSize": "13px",
                            "fontWeight": 500,
                            "color": TEXT_SECONDARY,
                            "marginBottom": "8px",
                            "display": "block",
                        },
                    ),
                    dcc.Slider(
                        id="sim-intensity-slider",
                        min=0.1,
                        max=1.0,
                        step=0.1,
                        value=0.8,
                        marks={
                            0.1: {"label": "Low"},
                            0.5: {"label": "Medium"},
                            1.0: {"label": "High"},
                        },
                        tooltip={
                            "placement": "bottom",
                            "always_visible": False,
                        },
                    ),
                ],
                style={"marginBottom": "24px"},
            ),
            # Trigger button
            html.Button(
                [
                    DashIconify(
                        icon="mdi:play",
                        width=18,
                        color="#FFFFFF",
                    ),
                    " Run Simulation",
                ],
                id="sim-trigger-btn",
                n_clicks=0,
                className="sim-trigger-btn",
                style={
                    "width": "100%",
                    "padding": "12px 24px",
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
            ),
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

    # ── Right panel: Results ───────────────────
    results_panel = html.Div(
        [
            # Damage summary KPIs
            html.Div(
                id="sim-damage-summary",
                children=_empty_damage_summary(),
                style={"marginBottom": f"{GAP_ELEMENT}px"},
            ),
            # Timeline chart
            chart_card("sim-timeline-chart", "Simulation Timeline"),
            # Affected zones list
            html.Div(
                id="sim-affected-zones",
                children=_empty_affected_zones(),
                style={"marginTop": f"{GAP_ELEMENT}px"},
            ),
        ],
        style={"flex": "1", "minWidth": 0},
    )

    # ── Two-column layout ──────────────────────
    two_col = html.Div(
        [left_col(event_trigger_panel), results_panel],
        style={
            "display": "flex",
            "gap": f"{GAP_ELEMENT}px",
            "alignItems": "flex-start",
        },
    )

    return html.Div(
        [result_store, page_header, two_col],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )


def left_col(children: html.Div) -> html.Div:
    """Wrap the trigger panel in a sticky left column.

    Args:
        children: The event trigger panel component.

    Returns:
        Dash html.Div wrapping the left column.
    """
    return html.Div(
        children,
        style={
            "width": "320px",
            "flexShrink": 0,
            "position": "sticky",
            "top": "80px",
        },
    )


def _empty_damage_summary() -> html.Div:
    """Return placeholder KPI cards for the damage summary.

    Returns:
        Dash html.Div with placeholder KPI cards.
    """
    return html.Div(
        [
            create_kpi_card(
                title="Total Damage",
                value="--",
                unit="\u20ac",
                icon="mdi:currency-eur",
            ),
            create_kpi_card(
                title="Evacuation Time",
                value="--",
                unit="s",
                icon="mdi:run-fast",
            ),
            create_kpi_card(
                title="Peak Distortion",
                value="--",
                icon="mdi:chart-bell-curve-cumulative",
            ),
            create_kpi_card(
                title="Zones Affected",
                value="--",
                icon="mdi:map-marker-alert-outline",
            ),
        ],
        className="grid-4",
    )


def _empty_affected_zones() -> html.Div:
    """Return placeholder for the affected zones section.

    Returns:
        Dash html.Div with empty state message.
    """
    return html.Div(
        html.Div(
            [
                DashIconify(
                    icon="mdi:information-outline",
                    width=20,
                    color=TEXT_TERTIARY,
                ),
                html.Span(
                    "Run a simulation to see affected zones and cascade effects.",
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
        },
    )
