"""Occupancy page: flow patterns and utilization rates.

Shows occupancy patterns by zone, utilization rates, peak hours,
and flow analysis across the CFT building.
"""

from __future__ import annotations

from dash import html

from views.components.kpi_card import create_kpi_card


def create_occupancy_page() -> html.Div:
    """Create the occupancy analysis page layout.

    Returns:
        Dash html.Div containing the occupancy page with pattern
        charts and utilization metrics.
    """
    kpi_grid = html.Div(
        [
            create_kpi_card(
                title="Current Occupancy",
                value="—",
                unit="people",
                icon="mdi:account-group",
            ),
            create_kpi_card(
                title="Utilization Rate",
                value="—",
                unit="%",
                icon="mdi:chart-donut",
            ),
            create_kpi_card(
                title="Peak Today",
                value="—",
                unit="people",
                icon="mdi:chart-bell-curve-cumulative",
            ),
            create_kpi_card(
                title="Active Zones",
                value="—",
                icon="mdi:map-marker-check",
            ),
        ],
        className="grid-4",
    )

    chart_placeholder = html.Div(
        "Occupancy flow patterns and utilization charts will be rendered here",
        className="card empty-state",
        style={"minHeight": "300px"},
        id="occupancy-charts",
    )

    return html.Div(
        [kpi_grid, chart_placeholder],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
