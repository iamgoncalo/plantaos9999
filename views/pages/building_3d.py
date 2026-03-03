"""3D building view page.

Wraps the Three.js 3D renderer in an html.Iframe component with
controls for metric selection, floor filtering, and camera reset.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify


def create_building_3d_page() -> html.Div:
    """Create the 3D building view page layout.

    Returns:
        Dash html.Div containing the 3D view iframe, metric selector,
        floor selector, reset button, and color legend.
    """
    # Metric selector (pill buttons)
    metric_selector = dcc.RadioItems(
        id="3d-metric-selector",
        options=[
            {"label": "Building Health", "value": "freedom_index"},
            {"label": "Temperature", "value": "temperature_c"},
            {"label": "Occupancy", "value": "occupant_count"},
            {"label": "Energy", "value": "total_energy_kwh"},
        ],
        value="freedom_index",
        className="time-range-selector",
        inline=True,
    )

    # Floor toggle
    floor_selector = dcc.RadioItems(
        id="3d-floor-selector",
        options=[
            {"label": "All Floors", "value": "all"},
            {"label": "Piso 0", "value": "0"},
            {"label": "Piso 1", "value": "1"},
        ],
        value="all",
        className="time-range-selector",
        inline=True,
    )

    # Reset camera button
    reset_btn = html.Button(
        [
            DashIconify(icon="mdi:camera-retake-outline", width=16),
            " Reset View",
        ],
        id="3d-reset-btn",
        className="viewer-3d-reset-btn",
        n_clicks=0,
    )

    # Controls overlay (positioned absolute over the iframe)
    controls = html.Div(
        [
            html.Div(
                [
                    html.Div("Metric", className="viewer-3d-control-label"),
                    metric_selector,
                ],
                className="viewer-3d-control-group",
            ),
            html.Div(
                [
                    html.Div("Floor", className="viewer-3d-control-label"),
                    floor_selector,
                ],
                className="viewer-3d-control-group",
            ),
            reset_btn,
        ],
        className="viewer-3d-controls",
    )

    # Color legend (bottom-left)
    legend = html.Div(
        [
            html.Span("Poor", className="viewer-3d-legend-label"),
            html.Div(className="viewer-3d-legend-gradient"),
            html.Span("Excellent", className="viewer-3d-legend-label"),
        ],
        className="viewer-3d-legend",
    )

    # 3D viewer iframe with loading placeholder
    _loading_html = (
        "<html><body style='margin:0;display:flex;align-items:center;"
        "justify-content:center;height:100vh;background:#FAFAFA;"
        "font-family:Inter,sans-serif;color:#86868B;font-size:15px'>"
        "Loading 3D View…</body></html>"
    )
    iframe = html.Iframe(
        id="3d-viewer-iframe",
        srcDoc=_loading_html,
        className="viewer-3d-iframe",
    )

    return html.Div(
        [
            html.Div(
                [
                    controls,
                    legend,
                    iframe,
                ],
                className="viewer-3d-container",
            ),
        ],
        className="page-enter",
    )
