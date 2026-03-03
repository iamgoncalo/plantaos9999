"""Comfort page: thermal and air quality analysis.

Displays temperature, humidity, CO2, and illuminance across zones
with threshold indicators, trend charts, and correlation analysis.
"""

from __future__ import annotations

from dash import dcc, html

from config.building import get_monitored_zones
from views.charts import chart_card
from views.components.kpi_card import create_kpi_card


def create_comfort_page() -> html.Div:
    """Create the comfort monitoring page layout.

    Returns:
        Dash html.Div containing the comfort page with KPIs,
        zone filter, and four interactive charts.
    """
    # Zone filter dropdown
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    controls = html.Div(
        [
            dcc.Dropdown(
                id="comfort-zone-filter",
                options=zone_options,
                multi=True,
                placeholder="All zones",
                className="zone-filter",
            ),
        ],
        className="page-controls",
    )

    # 4 KPI cards
    kpi_grid = html.Div(
        [
            create_kpi_card(
                title="Avg Temperature",
                value="—",
                unit="°C",
                icon="mdi:thermometer",
            ),
            create_kpi_card(
                title="Avg Humidity",
                value="—",
                unit="%",
                icon="mdi:water-percent",
            ),
            create_kpi_card(
                title="Avg CO₂",
                value="—",
                unit="ppm",
                icon="mdi:molecule-co2",
            ),
            create_kpi_card(
                title="In Comfort Band",
                value="—",
                unit="%",
                icon="mdi:check-circle-outline",
            ),
        ],
        className="grid-4",
        id="comfort-kpi-grid",
    )

    # Charts: 2×2 grid
    charts_row_1 = html.Div(
        [
            chart_card("comfort-chart-temperature", "Temperature by Zone"),
            chart_card("comfort-chart-matrix", "Comfort Compliance Matrix"),
        ],
        className="chart-grid",
    )

    charts_row_2 = html.Div(
        [
            chart_card("comfort-chart-co2", "CO₂ vs. Occupancy"),
            chart_card("comfort-chart-humidity", "Humidity Distribution"),
        ],
        className="chart-grid",
    )

    return html.Div(
        [controls, kpi_grid, charts_row_1, charts_row_2],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
