"""Comfort page: thermal and air quality heatmaps.

Displays temperature, humidity, CO2, and illuminance across zones
as heatmaps with threshold indicators and trend charts.
"""

from __future__ import annotations

from dash import html

from views.components.kpi_card import create_kpi_card


def create_comfort_page() -> html.Div:
    """Create the comfort monitoring page layout.

    Returns:
        Dash html.Div containing the comfort page with zone
        heatmaps and metric trend charts.
    """
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
                title="Zones in Comfort",
                value="—",
                icon="mdi:check-circle-outline",
            ),
        ],
        className="grid-4",
    )

    chart_placeholder = html.Div(
        "Comfort heatmaps and trend charts will be rendered here",
        className="card empty-state",
        style={"minHeight": "300px"},
        id="comfort-charts",
    )

    return html.Div(
        [kpi_grid, chart_placeholder],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
