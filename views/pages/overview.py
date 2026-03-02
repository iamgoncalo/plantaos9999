"""Overview page: floorplan, top KPIs, and alerts.

The main landing page showing building-wide status at a glance
with the interactive floorplan, key metrics, and recent alerts.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import ACCENT_BLUE, TEXT_TERTIARY
from views.components.alert_feed import create_alert_feed
from views.components.kpi_card import create_kpi_card


def create_overview_page() -> html.Div:
    """Create the overview page layout.

    Returns:
        Dash html.Div containing the overview page with floorplan,
        KPI grid, and alert feed.
    """
    kpi_grid = html.Div(
        [
            create_kpi_card(
                title="Total Energy",
                value="—",
                unit="kWh",
                icon="mdi:flash",
                trend=None,
            ),
            create_kpi_card(
                title="Occupancy",
                value="—",
                unit="people",
                icon="mdi:account-group",
                trend=None,
            ),
            create_kpi_card(
                title="Avg Temperature",
                value="—",
                unit="°C",
                icon="mdi:thermometer",
                trend=None,
            ),
            create_kpi_card(
                title="Building Health",
                value="—",
                unit="/100",
                icon="mdi:heart-pulse",
                trend=None,
            ),
        ],
        className="grid-4",
        id="overview-kpi-grid",
    )

    floorplan_placeholder = html.Div(
        [
            DashIconify(
                icon="mdi:floor-plan",
                width=48,
                color=TEXT_TERTIARY,
            ),
            html.Div(
                "Interactive floorplan will be rendered here",
                style={
                    "marginTop": "12px",
                    "fontSize": "14px",
                    "color": TEXT_TERTIARY,
                },
            ),
        ],
        className="card",
        style={
            "minHeight": "400px",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
        },
        id="overview-floorplan",
    )

    main_content = html.Div(
        [
            html.Div(
                [floorplan_placeholder],
                style={"flex": "1"},
            ),
            html.Div(
                [create_alert_feed()],
                style={"width": "380px", "flexShrink": 0},
            ),
        ],
        style={
            "display": "flex",
            "gap": "16px",
            "marginTop": "16px",
        },
    )

    return html.Div(
        [kpi_grid, main_content],
        className="page-enter",
    )
