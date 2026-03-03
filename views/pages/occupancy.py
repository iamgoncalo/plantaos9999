"""Occupancy page: flow patterns and utilization rates.

Shows occupancy patterns by zone, utilization rates, peak hours,
flow analysis, and space efficiency across the CFT building.
"""

from __future__ import annotations

from dash import dcc, html

from views.charts import chart_card
from views.components.kpi_card import create_kpi_card


def create_occupancy_page() -> html.Div:
    """Create the occupancy analysis page layout.

    Returns:
        Dash html.Div containing the occupancy page with KPIs,
        time-range selector, and four interactive charts.
    """
    # Time range selector
    time_selector = html.Div(
        [
            dcc.RadioItems(
                id="occ-time-range",
                options=[
                    {"label": "Today", "value": "today"},
                    {"label": "7 Days", "value": "7d"},
                    {"label": "30 Days", "value": "30d"},
                ],
                value="today",
                className="time-range-selector",
                inline=True,
            ),
        ],
        className="page-controls",
    )

    # 4 KPI cards
    kpi_grid = html.Div(
        [
            create_kpi_card(
                title="Current Occupancy",
                value="—",
                unit="people",
                icon="mdi:account-group",
            ),
            create_kpi_card(
                title="Peak Today",
                value="—",
                unit="people",
                icon="mdi:chart-bell-curve-cumulative",
            ),
            create_kpi_card(
                title="Avg Utilization",
                value="—",
                unit="%",
                icon="mdi:chart-donut",
            ),
            create_kpi_card(
                title="Busiest Zone",
                value="—",
                icon="mdi:map-marker-check",
            ),
        ],
        className="grid-4",
        id="occ-kpi-grid",
    )

    # Charts: 2×2 grid
    charts_row_1 = html.Div(
        [
            chart_card("occ-chart-timeline", "Occupancy Timeline"),
            chart_card("occ-chart-heatmap", "Zone Utilization (% Capacity)"),
        ],
        className="chart-grid",
    )

    charts_row_2 = html.Div(
        [
            chart_card("occ-chart-sankey", "People Flow Between Zones"),
            chart_card("occ-chart-efficiency", "Space Efficiency by Zone"),
        ],
        className="chart-grid",
    )

    return html.Div(
        [time_selector, kpi_grid, charts_row_1, charts_row_2],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
