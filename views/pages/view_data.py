"""Data Explorer page: browse, filter, and export raw datasets.

Provides a tabular view of any dataset in the DataStore with zone and
time-range filtering, an inline line chart preview, and CSV export.
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
    TEXT_PRIMARY,
)


def create_data_explorer_page() -> html.Div:
    """Create the Data Explorer page layout.

    Returns:
        Dash html.Div containing the data explorer with filter panel,
        data table, chart preview, and CSV export.
    """
    # Zone dropdown options from monitored zones
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    # Page header
    header = html.Div(
        [
            DashIconify(
                icon="mdi:table-search",
                width=24,
                color=ACCENT_BLUE,
            ),
            html.H2(
                "Data Explorer",
                style={
                    "margin": 0,
                    "fontSize": "20px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "fontFamily": FONT_STACK,
                },
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
        },
    )

    # Filter panel card
    filter_panel = html.Div(
        [
            dcc.Dropdown(
                id="data-explorer-dataset",
                options=["energy", "comfort", "occupancy", "weather", "schedule"],
                value="comfort",
                clearable=False,
                style={"minWidth": "160px"},
            ),
            dcc.Dropdown(
                id="data-explorer-zone",
                options=zone_options,
                placeholder="All zones",
                clearable=True,
                style={"minWidth": "200px"},
            ),
            dcc.RadioItems(
                id="data-explorer-range",
                options=["1d", "7d", "30d"],
                value="7d",
                className="time-range-selector",
                inline=True,
            ),
            html.Button(
                "Export CSV",
                id="data-explorer-export-btn",
                n_clicks=0,
                style={
                    "padding": "8px 16px",
                    "borderRadius": "12px",
                    "border": "none",
                    "background": ACCENT_BLUE,
                    "color": "#FFFFFF",
                    "fontSize": "13px",
                    "fontWeight": 500,
                    "cursor": "pointer",
                    "fontFamily": FONT_STACK,
                    "whiteSpace": "nowrap",
                },
            ),
            dcc.Download(id="data-explorer-download"),
        ],
        style={
            "display": "flex",
            "flexDirection": "row",
            "alignItems": "center",
            "gap": f"{GAP_ELEMENT}px",
            "flexWrap": "wrap",
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    # Data table container
    table_container = html.Div(
        id="data-explorer-table",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "overflowX": "auto",
        },
    )

    # Chart preview
    chart = dcc.Graph(
        id="data-explorer-chart",
        config={
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
        style={"height": "320px"},
    )

    return html.Div(
        [header, filter_panel, table_container, chart],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )
