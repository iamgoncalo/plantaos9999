"""Simulation page helper functions.

Contains empty-state builders and ROI data used by the simulation
callbacks. Extracted to keep simulation_cb.py under the LOC target.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import (
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    TEXT_TERTIARY,
)
from views.components.kpi_card import create_kpi_card


# Per-scenario ROI data for optimization modes
SCENARIO_ROI: dict[str, dict] = {
    "hvac_failure": {"invest": 0, "impl": "1-3", "desc": "HVAC schedule"},
    "open_window": {"invest": 200, "impl": "3-5", "desc": "Window sensors"},
    "mass_entry": {"invest": 0, "impl": "1-3", "desc": "Occupancy plan"},
    "hvac_night_off": {
        "invest": 0,
        "impl": "1-2",
        "desc": "Schedule change",
    },
    "presence_sensors": {
        "invest": 2400,
        "impl": "7-14",
        "desc": "Sensors",
    },
    "setpoint_adjust": {"invest": 0, "impl": "1", "desc": "Config change"},
    "zone_consolidation": {"invest": 0, "impl": "3-7", "desc": "Policy"},
}


def empty_damage_summary() -> html.Div:
    """Return placeholder KPI cards for the savings summary.

    Returns:
        Dash html.Div with placeholder KPI cards showing '--' values.
    """
    return html.Div(
        [
            create_kpi_card(
                title="Monthly Savings",
                value="--",
                unit="\u20ac",
                icon="mdi:piggy-bank-outline",
            ),
            create_kpi_card(
                title="Implementation",
                value="--",
                unit="days",
                icon="mdi:clock-outline",
            ),
            create_kpi_card(
                title="Comfort Impact",
                value="--",
                icon="mdi:thermometer-check",
            ),
            create_kpi_card(
                title="Zones Affected",
                value="--",
                icon="mdi:map-marker-alert-outline",
            ),
        ],
        className="grid-4",
    )


def empty_affected_zones() -> html.Div:
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
                    "Run a scenario to see optimization recommendations "
                    "and projected savings.",
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
