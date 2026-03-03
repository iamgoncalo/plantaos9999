"""Overview page: floorplan, top KPIs, and alerts.

The main landing page showing building-wide status at a glance
with the interactive floorplan, key metrics, and recent alerts.
"""

from __future__ import annotations

from dash import dcc, html

from config.theme import TEXT_TERTIARY
from views.components.alert_feed import create_alert_feed
from views.components.insight_card import create_insight_card
from views.components.kpi_card import create_kpi_skeleton


def create_overview_page() -> html.Div:
    """Create the overview page layout.

    Returns:
        Dash html.Div containing the overview page with floorplan,
        KPI grid, and alert feed.
    """
    # Row 1: 5 skeleton KPI cards (replaced by callback when data loads)
    kpi_grid = html.Div(
        [create_kpi_skeleton() for _ in range(5)],
        className="grid-5",
        id="overview-kpi-grid",
    )

    # Row 2 Left: Floor tabs + floorplan graph
    floor_tabs = html.Div(
        [
            html.Button(
                "Piso 0", id="floor-tab-0", className="floor-tab active", n_clicks=0
            ),
            html.Button("Piso 1", id="floor-tab-1", className="floor-tab", n_clicks=0),
        ],
        className="floor-tabs",
    )

    floorplan_graph = dcc.Graph(
        id="floorplan-graph",
        config={"displayModeBar": False, "staticPlot": False},
        style={"height": "500px"},
    )

    legend = html.Div(
        [
            html.Span("Poor"),
            html.Div(className="floorplan-legend-gradient"),
            html.Span("Excellent"),
            html.Span("— Freedom Index", style={"marginLeft": "8px"}),
        ],
        className="floorplan-legend",
    )

    floorplan_section = html.Div(
        [floor_tabs, floorplan_graph, legend],
        className="floorplan-container",
    )

    # Row 2 Right: Zone detail panel (empty until zone is clicked)
    zone_panel = html.Div(
        id="overview-zone-panel",
        children=[
            html.Div(
                [
                    html.Div(
                        "Click a zone on the floorplan to see details",
                        style={"color": TEXT_TERTIARY, "fontSize": "14px"},
                    ),
                ],
                className="empty-state",
            ),
        ],
        className="zone-detail",
    )

    main_row = html.Div(
        [
            html.Div([floorplan_section], className="overview-floorplan-section"),
            html.Div([zone_panel], className="overview-zone-section"),
        ],
        className="overview-row-main",
    )

    # Row 3: Alert feed + Latest insight
    bottom_row = html.Div(
        [
            html.Div(
                id="overview-alert-feed",
                children=[create_alert_feed()],
            ),
            html.Div(
                id="overview-insight",
                children=[
                    create_insight_card(
                        insight=(
                            "Building operating within normal parameters. "
                            "All systems are being monitored by PlantaOS."
                        ),
                        category="general",
                        severity="info",
                    ),
                ],
            ),
        ],
        className="overview-row-bottom",
    )

    return html.Div(
        [
            dcc.Store(id="active-floor-store", data=0),
            kpi_grid,
            main_row,
            bottom_row,
        ],
        className="page-enter",
    )
