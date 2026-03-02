"""Energy page: breakdown, baselines, and anomalies.

Shows energy consumption by zone and category (HVAC 60%, lighting 20%,
equipment 15%, other 5%), baseline comparisons, and detected anomalies.
"""

from __future__ import annotations

from dash import html

from config.theme import TEXT_TERTIARY
from views.components.kpi_card import create_kpi_card


def create_energy_page() -> html.Div:
    """Create the energy analysis page layout.

    Returns:
        Dash html.Div containing the energy page with breakdown
        charts, baseline comparison, and anomaly markers.
    """
    kpi_grid = html.Div(
        [
            create_kpi_card(
                title="Today's Consumption",
                value="—",
                unit="kWh",
                icon="mdi:flash",
            ),
            create_kpi_card(
                title="HVAC Load",
                value="—",
                unit="kWh",
                icon="mdi:air-conditioner",
            ),
            create_kpi_card(
                title="vs. Baseline",
                value="—",
                unit="%",
                icon="mdi:chart-line",
            ),
            create_kpi_card(
                title="Anomalies",
                value="—",
                icon="mdi:alert-circle-outline",
            ),
        ],
        className="grid-4",
    )

    chart_placeholder = html.Div(
        "Energy breakdown charts will be rendered here",
        className="card empty-state",
        style={"minHeight": "300px"},
        id="energy-charts",
    )

    return html.Div(
        [kpi_grid, chart_placeholder],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
