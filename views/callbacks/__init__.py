"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations

from dash import Input, Output, State, html
from dash_iconify import DashIconify
from loguru import logger

from views.components.safe_callback import safe_callback

from views.callbacks.admin_cb import register_admin_callbacks
from views.callbacks.booking_cb import register_booking_callbacks
from views.callbacks.building_3d_cb import register_3d_callbacks
from views.callbacks.comfort_cb import register_comfort_callbacks
from views.callbacks.deployment_cb import register_deployment_callbacks
from views.callbacks.energy_cb import register_energy_callbacks
from views.callbacks.insights_cb import register_insights_callbacks
from views.callbacks.nav_cb import register_nav_callbacks
from views.callbacks.occupancy_cb import register_occupancy_callbacks
from views.callbacks.reports_cb import register_reports_callbacks
from views.callbacks.simulation_cb import register_simulation_callbacks
from views.callbacks.state_cb import register_state_callbacks
from views.callbacks.view_2d_cb import register_view_2d_callbacks
from views.callbacks.view_4d_cb import register_view_4d_callbacks
from views.callbacks.view_data_cb import register_data_explorer_callbacks
from views.callbacks.view_emergency_cb import register_emergency_callbacks
from views.callbacks.view_context_cb import register_context_callbacks
from views.callbacks.view_sensors_cb import register_sensor_coverage_callbacks

# Optional callback modules (created by other agents)
try:
    from views.callbacks.sensors_cb import register_sensors_callbacks
except ImportError:
    register_sensors_callbacks = None

try:
    from views.callbacks.view_flow_cb import register_flow_callbacks
except ImportError:
    register_flow_callbacks = None

try:
    from views.callbacks.view_heatmap_cb import register_heatmap_callbacks
except ImportError:
    register_heatmap_callbacks = None


# Page title mapping: pathname -> display title
_PAGE_TITLES: dict[str, str] = {
    "/": "Overview",
    "/overview": "Overview",
    "/energy": "Energy",
    "/comfort": "Comfort",
    "/occupancy": "Occupancy",
    "/insights": "Insights",
    "/building_3d": "3D Building",
    "/building_3d_walk": "3D Walk",
    "/view_2d": "2D Map",
    "/view_4d": "4D Explorer",
    "/view_sensors": "Sensor Coverage",
    "/view_emergency": "Emergency Mode",
    "/view_data": "Data Explorer",
    "/view_flow": "Flow",
    "/view_heatmap": "Heatmap",
    "/simulation": "Simulation",
    "/reports": "Reports",
    "/sensors": "Sensors",
    "/booking": "Smart Booking",
    "/admin": "Settings",
    "/view_map": "Map Overlay",
    "/view_context": "Context",
}


def register_callbacks(app: object) -> None:
    """Register all dashboard callbacks with the Dash app.

    Args:
        app: The Dash application instance.
    """
    _register_routing_callback(app)
    # State callbacks (building state, KPIs, floorplan, alerts)
    register_state_callbacks(app)
    # Navigation callbacks (clock, sidebar, search, notifications)
    register_nav_callbacks(app)
    # Detail page callbacks
    register_energy_callbacks(app)
    register_comfort_callbacks(app)
    register_occupancy_callbacks(app)
    register_insights_callbacks(app)
    register_3d_callbacks(app)
    # New AFI pages
    register_simulation_callbacks(app)
    register_reports_callbacks(app)
    register_deployment_callbacks(app)
    register_view_2d_callbacks(app)
    register_view_4d_callbacks(app)
    register_sensor_coverage_callbacks(app)
    register_emergency_callbacks(app)
    register_data_explorer_callbacks(app)
    register_booking_callbacks(app)
    register_admin_callbacks(app)
    register_context_callbacks(app)
    # Optional callback modules (created by other agents)
    if register_sensors_callbacks is not None:
        register_sensors_callbacks(app)
    if register_flow_callbacks is not None:
        register_flow_callbacks(app)
    if register_heatmap_callbacks is not None:
        register_heatmap_callbacks(app)


def _register_routing_callback(app: object) -> None:
    """Register the URL routing callback."""

    _PROTECTED_PATHS = {"/reports", "/sensors", "/deployment"}

    @app.callback(
        Output("page-content", "children"),
        Output("header-title", "children"),
        Input("url", "pathname"),
        State("auth-store", "data"),
    )
    @safe_callback
    def route_page(pathname: str, auth_data: dict | None) -> tuple:
        """Route URL pathname to the correct page component."""
        try:
            from views.pages.admin import create_admin_page
            from views.pages.booking import create_booking_page
            from views.pages.building_3d import create_building_3d_page
            from views.pages.comfort import create_comfort_page
            from views.pages.deployment import create_deployment_page
            from views.pages.energy import create_energy_page
            from views.pages.insights_page import create_insights_page
            from views.pages.occupancy import create_occupancy_page
            from views.pages.overview import create_overview_page
            from views.pages.reports import create_reports_page
            from views.pages.simulation import create_simulation_page
            from views.pages.view_2d import create_view_2d_page
            from views.pages.view_4d import create_view_4d_page
            from views.pages.view_data import create_data_explorer_page
            from views.pages.view_emergency import create_emergency_page
            from views.pages.view_context import create_context_page
            from views.pages.view_map import create_map_overlay_page
            from views.pages.view_sensors import create_sensor_coverage_page

            # Optional page imports (created by other agents)
            try:
                from views.pages.sensors import create_sensors_page
            except ImportError:
                create_sensors_page = None

            try:
                from views.pages.view_flow import create_flow_page
            except ImportError:
                create_flow_page = None

            try:
                from views.pages.view_heatmap import create_heatmap_page
            except ImportError:
                create_heatmap_page = None

            page_map: dict = {
                "/": create_overview_page,
                "/overview": create_overview_page,
                "/energy": create_energy_page,
                "/comfort": create_comfort_page,
                "/occupancy": create_occupancy_page,
                "/insights": create_insights_page,
                "/building_3d": create_building_3d_page,
                "/building_3d_walk": create_building_3d_page,
                "/view_2d": create_view_2d_page,
                "/view_4d": create_view_4d_page,
                "/view_sensors": create_sensor_coverage_page,
                "/view_emergency": create_emergency_page,
                "/view_data": create_data_explorer_page,
                "/simulation": create_simulation_page,
                "/reports": create_reports_page,
                "/deployment": create_deployment_page,
                "/booking": create_booking_page,
                "/admin": create_admin_page,
                "/view_map": create_map_overlay_page,
                "/view_context": create_context_page,
            }

            # Add optional pages if available
            if create_sensors_page is not None:
                page_map["/sensors"] = create_sensors_page
            if create_flow_page is not None:
                page_map["/view_flow"] = create_flow_page
            if create_heatmap_page is not None:
                page_map["/view_heatmap"] = create_heatmap_page

            title = _PAGE_TITLES.get(pathname, "Not Found")

            # Auth gate: protected paths require login
            if pathname in _PROTECTED_PATHS and not auth_data:
                return html.Div(
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:lock-outline",
                                width=48,
                                color="#86868B",
                            ),
                            html.H2(
                                "Authentication Required",
                                style={
                                    "margin": "16px 0 8px",
                                    "fontSize": "20px",
                                    "fontWeight": 600,
                                },
                            ),
                            html.P(
                                "Please log in via Settings to access this page.",
                                style={
                                    "color": "#6E6E73",
                                    "marginBottom": "24px",
                                },
                            ),
                            html.A(
                                "Go to Settings",
                                href="/admin",
                                className="status-badge healthy",
                                style={
                                    "textDecoration": "none",
                                    "padding": "8px 20px",
                                    "fontSize": "14px",
                                },
                            ),
                        ],
                        className="card",
                        style={
                            "textAlign": "center",
                            "padding": "48px",
                            "maxWidth": "480px",
                            "margin": "80px auto",
                        },
                    ),
                    className="page-enter",
                ), title

            creator = page_map.get(pathname)

            if creator:
                return creator(), title

            # Enhanced 404 page
            return html.Div(
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:map-marker-question-outline",
                            width=48,
                            color="#86868B",
                        ),
                        html.H2(
                            "404 \u2014 Page Not Found",
                            style={
                                "margin": "16px 0 8px",
                                "fontSize": "20px",
                                "fontWeight": 600,
                            },
                        ),
                        html.P(
                            f"The path '{pathname}' does not exist.",
                            style={"color": "#6E6E73", "marginBottom": "24px"},
                        ),
                        html.A(
                            "Go to Overview",
                            href="/",
                            className="status-badge healthy",
                            style={
                                "textDecoration": "none",
                                "padding": "8px 20px",
                                "fontSize": "14px",
                            },
                        ),
                    ],
                    className="card",
                    style={
                        "textAlign": "center",
                        "padding": "48px",
                        "maxWidth": "480px",
                        "margin": "80px auto",
                    },
                ),
                className="page-enter",
            ), title
        except Exception as e:
            logger.warning(f"Routing callback error: {e}")
            return html.Div("Error loading page"), "Error"
