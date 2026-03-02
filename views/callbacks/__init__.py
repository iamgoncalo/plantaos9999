"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations

from datetime import datetime

from dash import Input, Output, html

from utils.time_utils import current_shift


# Page title mapping: pathname → display title
_PAGE_TITLES: dict[str, str] = {
    "/": "Overview",
    "/overview": "Overview",
    "/energy": "Energy",
    "/comfort": "Comfort",
    "/occupancy": "Occupancy",
    "/insights": "Insights",
    "/building_3d": "3D View",
}

_SHIFT_LABELS: dict[str, str] = {
    "morning": "Morning Shift",
    "afternoon": "Afternoon Shift",
    "night": "Night Shift",
    "off_hours": "Off Hours",
}


def register_callbacks(app: object) -> None:
    """Register all dashboard callbacks with the Dash app.

    Args:
        app: The Dash application instance.
    """
    _register_routing_callback(app)
    _register_clock_callback(app)


def _register_routing_callback(app: object) -> None:
    """Register the URL routing callback."""

    @app.callback(
        Output("page-content", "children"),
        Output("header-title", "children"),
        Input("url", "pathname"),
    )
    def route_page(pathname: str) -> tuple:
        """Route URL pathname to the correct page component."""
        from views.pages.building_3d import create_building_3d_page
        from views.pages.comfort import create_comfort_page
        from views.pages.energy import create_energy_page
        from views.pages.insights_page import create_insights_page
        from views.pages.occupancy import create_occupancy_page
        from views.pages.overview import create_overview_page

        page_map = {
            "/": create_overview_page,
            "/overview": create_overview_page,
            "/energy": create_energy_page,
            "/comfort": create_comfort_page,
            "/occupancy": create_occupancy_page,
            "/insights": create_insights_page,
            "/building_3d": create_building_3d_page,
        }

        title = _PAGE_TITLES.get(pathname, "Not Found")
        creator = page_map.get(pathname)

        if creator:
            return creator(), title

        return html.Div(
            [
                html.H2("404 — Page Not Found"),
                html.P(
                    f"The path '{pathname}' does not exist.",
                    style={"color": "#6E6E73"},
                ),
            ],
            className="page-enter",
            style={"textAlign": "center", "paddingTop": "80px"},
        ), title


def _register_clock_callback(app: object) -> None:
    """Register the header clock + shift indicator callback."""

    @app.callback(
        Output("header-clock", "children"),
        Output("header-shift", "children"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_clock(_n: int) -> tuple[str, str]:
        """Update the header clock and shift indicator."""
        now = datetime.now()
        clock_str = now.strftime("%H:%M:%S")
        shift = current_shift(now)
        shift_label = _SHIFT_LABELS.get(shift, shift.title())
        return clock_str, shift_label
