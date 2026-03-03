"""Reports page: financial P&L statements and cost analysis with PDF export."""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import ACCENT_BLUE
from views.charts import chart_card
from views.components.kpi_card import create_kpi_card


def create_reports_page() -> html.Div:
    """Create the financial reports page layout."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:file-chart-outline",
                                width=24,
                                color=ACCENT_BLUE,
                            ),
                            html.H2(
                                "Financial Reports",
                                style={
                                    "margin": 0,
                                    "fontSize": "20px",
                                    "fontWeight": 600,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                        },
                    ),
                    html.Div(
                        [
                            dcc.RadioItems(
                                id="reports-period",
                                options=[
                                    {"label": "Today", "value": "today"},
                                    {"label": "7 Days", "value": "7d"},
                                    {"label": "30 Days", "value": "30d"},
                                ],
                                value="today",
                                className="time-range-selector",
                                inline=True,
                            ),
                            html.Button(
                                [
                                    DashIconify(
                                        icon="mdi:file-pdf-box",
                                        width=18,
                                        color="#FFFFFF",
                                    ),
                                    html.Span(
                                        "Download PDF",
                                        style={"marginLeft": "6px"},
                                    ),
                                ],
                                id="reports-download-pdf-btn",
                                n_clicks=0,
                                style={
                                    "display": "inline-flex",
                                    "alignItems": "center",
                                    "padding": "8px 16px",
                                    "borderRadius": "10px",
                                    "border": "none",
                                    "background": ACCENT_BLUE,
                                    "color": "#FFFFFF",
                                    "fontSize": "13px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "fontFamily": (
                                        "'Inter', -apple-system, sans-serif"
                                    ),
                                },
                            ),
                        ],
                        className="page-controls",
                        style={"gap": "12px"},
                    ),
                ],
                className="page-controls",
                style={"justifyContent": "space-between"},
            ),
            html.Div(
                [
                    create_kpi_card(
                        title="Total Energy Cost",
                        value="—",
                        unit="€",
                        icon="mdi:flash",
                    ),
                    create_kpi_card(
                        title="Productivity Impact",
                        value="—",
                        unit="€",
                        icon="mdi:account-group",
                    ),
                    create_kpi_card(
                        title="HVAC Waste",
                        value="—",
                        unit="€",
                        icon="mdi:window-open-variant",
                    ),
                    create_kpi_card(
                        title="Net Savings",
                        value="—",
                        unit="€",
                        icon="mdi:piggy-bank-outline",
                    ),
                ],
                className="grid-4",
                id="reports-kpi-grid",
            ),
            html.Div(
                [
                    chart_card("reports-chart-breakdown", "Cost Breakdown by Category"),
                    chart_card("reports-chart-trend", "Daily Cost Trend (€)"),
                ],
                className="chart-grid",
            ),
            html.Div(
                [
                    chart_card("reports-chart-zones", "Cost by Zone (Top 10)"),
                    chart_card("reports-chart-savings", "Savings vs. Baseline"),
                ],
                className="chart-grid",
            ),
            # PDF download component (hidden)
            dcc.Download(id="reports-pdf-download"),
        ],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
