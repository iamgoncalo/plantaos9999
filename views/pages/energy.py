"""Energy page: breakdown, baselines, and anomalies.

Shows energy consumption by zone and category (HVAC 60%, lighting 20%,
equipment 15%, other 5%), baseline comparisons, and detected anomalies.
"""

from __future__ import annotations

from dash import dcc, html

from views.charts import chart_card
from views.components.kpi_card import create_kpi_card


def create_energy_page() -> html.Div:
    """Create the energy analysis page layout.

    Returns:
        Dash html.Div containing the energy page with KPIs,
        time-range selector, and four interactive charts.
    """
    # Time range selector
    time_selector = html.Div(
        [
            dcc.RadioItems(
                id="energy-time-range",
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
                title="Total Consumption",
                value="—",
                unit="kWh",
                icon="mdi:flash",
            ),
            create_kpi_card(
                title="vs. Baseline",
                value="—",
                unit="%",
                icon="mdi:chart-line",
            ),
            create_kpi_card(
                title="Peak Hour",
                value="—",
                icon="mdi:clock-alert-outline",
            ),
            create_kpi_card(
                title="Cost Estimate",
                value="—",
                unit="€",
                icon="mdi:currency-eur",
            ),
        ],
        className="grid-4",
        id="energy-kpi-grid",
    )

    # Charts: 2×2 grid
    charts_row_1 = html.Div(
        [
            chart_card("energy-chart-timeline", "Energy vs. Baseline"),
            chart_card("energy-chart-breakdown", "Consumption by Category"),
        ],
        className="chart-grid",
    )

    charts_row_2 = html.Div(
        [
            chart_card("energy-chart-heatmap", "Zone Energy Heatmap"),
            chart_card("energy-chart-scatter", "Energy vs. Occupancy"),
        ],
        className="chart-grid",
    )

    return html.Div(
        [time_selector, kpi_grid, charts_row_1, charts_row_2],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
