"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations

from datetime import datetime

from dash import Input, Output, State, ctx, html

from utils.time_utils import current_shift
from views.callbacks.comfort_cb import register_comfort_callbacks
from views.callbacks.energy_cb import register_energy_callbacks
from views.callbacks.insights_cb import register_insights_callbacks
from views.callbacks.occupancy_cb import register_occupancy_callbacks


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
    _register_building_state_callback(app)
    _register_overview_kpi_callback(app)
    _register_floorplan_callback(app)
    _register_floor_tab_callback(app)
    _register_zone_click_callback(app)
    _register_alert_feed_callback(app)
    _register_header_status_callback(app)
    # Detail page callbacks
    register_energy_callbacks(app)
    register_comfort_callbacks(app)
    register_occupancy_callbacks(app)
    register_insights_callbacks(app)


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


def _register_building_state_callback(app: object) -> None:
    """Refresh building state every interval tick."""

    @app.callback(
        Output("building-state-store", "data"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def refresh_building_state(_n: int) -> dict:
        """Compute and store building state."""
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        return state.model_dump(mode="json")


def _register_overview_kpi_callback(app: object) -> None:
    """Update overview KPI cards from building state."""

    @app.callback(
        Output("overview-kpi-grid", "children"),
        Input("building-state-store", "data"),
    )
    def update_kpis(state_data: dict | None) -> list:
        """Regenerate KPI cards with live data."""
        from utils.formatters import format_energy
        from views.components.kpi_card import create_kpi_card

        if not state_data:
            return [
                create_kpi_card("Total Energy", "—", icon="mdi:flash"),
                create_kpi_card("Avg Temperature", "—", icon="mdi:thermometer"),
                create_kpi_card("Occupancy", "—", icon="mdi:account-group"),
                create_kpi_card("Active Alerts", "—", icon="mdi:alert-circle-outline"),
                create_kpi_card("Building Health", "—", icon="mdi:heart-pulse"),
            ]

        energy = state_data.get("total_energy_kwh", 0)
        occupancy = state_data.get("total_occupancy", 0)
        freedom = state_data.get("avg_freedom_index", 0)
        alerts = state_data.get("active_alerts", 0)

        # Compute avg temperature from floor states
        floors = state_data.get("floors", [])
        temps = [f["avg_temperature"] for f in floors if f.get("avg_temperature")]
        avg_temp = sum(temps) / len(temps) if temps else 0

        return [
            create_kpi_card(
                "Total Energy",
                format_energy(energy),
                icon="mdi:flash",
            ),
            create_kpi_card(
                "Avg Temperature",
                f"{avg_temp:.1f}",
                unit="°C",
                icon="mdi:thermometer",
            ),
            create_kpi_card(
                "Occupancy",
                str(occupancy),
                unit="people",
                icon="mdi:account-group",
            ),
            create_kpi_card(
                "Active Alerts",
                str(alerts),
                icon="mdi:alert-circle-outline",
            ),
            create_kpi_card(
                "Building Health",
                f"{freedom:.0f}",
                unit="/100",
                icon="mdi:heart-pulse",
            ),
        ]


def _register_floorplan_callback(app: object) -> None:
    """Update floorplan figure from building state and active floor."""

    @app.callback(
        Output("floorplan-graph", "figure"),
        Input("building-state-store", "data"),
        Input("active-floor-store", "data"),
    )
    def update_floorplan(state_data: dict | None, active_floor: int | None):
        """Re-render floorplan with current zone data."""
        from views.floorplan.renderer_2d import render_floorplan_2d

        floor = active_floor if active_floor is not None else 0

        if not state_data:
            return render_floorplan_2d(floor=floor)

        # Build zone_data dict from building state
        zone_data: dict = {}
        for floor_state in state_data.get("floors", []):
            for zone in floor_state.get("zones", []):
                zone_data[zone["zone_id"]] = {
                    "freedom_index": zone.get("freedom_index", 50),
                    "temperature_c": zone.get("temperature_c"),
                    "humidity_pct": zone.get("humidity_pct"),
                    "co2_ppm": zone.get("co2_ppm"),
                    "illuminance_lux": zone.get("illuminance_lux"),
                    "occupant_count": zone.get("occupant_count", 0),
                    "total_energy_kwh": zone.get("total_energy_kwh", 0),
                    "status": zone.get("status", "unknown"),
                }

        return render_floorplan_2d(floor=floor, zone_data=zone_data)


def _register_floor_tab_callback(app: object) -> None:
    """Switch active floor when floor tabs are clicked."""

    @app.callback(
        Output("active-floor-store", "data"),
        Output("floor-tab-0", "className"),
        Output("floor-tab-1", "className"),
        Input("floor-tab-0", "n_clicks"),
        Input("floor-tab-1", "n_clicks"),
    )
    def switch_floor(
        n0: int | None,
        n1: int | None,
    ) -> tuple[int, str, str]:
        """Handle floor tab clicks."""
        triggered = ctx.triggered_id
        if triggered == "floor-tab-1":
            return 1, "floor-tab", "floor-tab active"
        return 0, "floor-tab active", "floor-tab"


def _register_zone_click_callback(app: object) -> None:
    """Update zone detail panel when a zone is clicked on the floorplan."""

    @app.callback(
        Output("overview-zone-panel", "children"),
        Input("floorplan-graph", "clickData"),
        State("building-state-store", "data"),
    )
    def show_zone_detail(
        click_data: dict | None,
        state_data: dict | None,
    ) -> list:
        """Render zone detail from click event."""
        from views.components.zone_panel import create_zone_detail

        if not click_data or not state_data:
            return [
                html.Div(
                    "Click a zone on the floorplan to see details",
                    className="empty-state",
                )
            ]

        # Extract zone_id from clickData
        points = click_data.get("points", [])
        zone_id = None
        for point in points:
            cd = point.get("customdata")
            if cd:
                zone_id = cd if isinstance(cd, str) else cd[0] if cd else None
                break

        if not zone_id:
            return [
                html.Div(
                    "Click a zone on the floorplan to see details",
                    className="empty-state",
                )
            ]

        # Find zone state data
        zone_state = None
        for floor_state in state_data.get("floors", []):
            for z in floor_state.get("zones", []):
                if z.get("zone_id") == zone_id:
                    zone_state = z
                    break

        return [create_zone_detail(zone_id=zone_id, zone_state=zone_state)]


def _register_alert_feed_callback(app: object) -> None:
    """Update alert feed from building state."""

    @app.callback(
        Output("overview-alert-feed", "children"),
        Input("building-state-store", "data"),
    )
    def update_alert_feed(state_data: dict | None):
        """Generate alerts from zones with warning/critical status."""
        from config.building import get_zone_by_id
        from views.components.alert_feed import create_alert_feed

        if not state_data:
            return create_alert_feed()

        alerts: list[dict] = []
        for floor_state in state_data.get("floors", []):
            for zone in floor_state.get("zones", []):
                status = zone.get("status", "unknown")
                if status in ("warning", "critical"):
                    zone_info = get_zone_by_id(zone["zone_id"])
                    name = zone_info.name if zone_info else zone["zone_id"]
                    severity = "critical" if status == "critical" else "warning"

                    msg = _build_alert_message(zone, name)
                    alerts.append(
                        {
                            "message": msg,
                            "severity": severity,
                            "timestamp": zone.get("timestamp", ""),
                            "zone_id": zone["zone_id"],
                        }
                    )

        # Critical alerts first
        alerts.sort(key=lambda a: a["severity"] == "critical", reverse=True)
        return create_alert_feed(alerts=alerts)


def _register_header_status_callback(app: object) -> None:
    """Update header alert count and status badge from building state."""

    @app.callback(
        Output("header-alert-count", "children"),
        Output("header-status", "className"),
        Input("building-state-store", "data"),
    )
    def update_header_status(
        state_data: dict | None,
    ) -> tuple[str, str]:
        """Update header indicators."""
        if not state_data:
            return "0", "status-badge healthy"

        alerts = state_data.get("active_alerts", 0)

        if alerts > 5:
            badge_class = "status-badge critical"
        elif alerts > 0:
            badge_class = "status-badge warning"
        else:
            badge_class = "status-badge healthy"

        return str(alerts), badge_class


def _build_alert_message(zone_data: dict, name: str) -> str:
    """Build a descriptive alert message from zone metrics.

    Args:
        zone_data: Zone state dict with metric values.
        name: Zone display name.

    Returns:
        Human-readable alert message.
    """
    issues: list[str] = []

    co2 = zone_data.get("co2_ppm")
    if co2 is not None and co2 > 1000:
        issues.append(f"CO₂ at {co2:.0f} ppm")

    temp = zone_data.get("temperature_c")
    if temp is not None and (temp > 26 or temp < 18):
        direction = "above" if temp > 26 else "below"
        issues.append(f"Temperature {direction} range ({temp:.1f} °C)")

    hum = zone_data.get("humidity_pct")
    if hum is not None and (hum > 70 or hum < 30):
        issues.append(f"Humidity at {hum:.0f}%")

    if issues:
        return f"{name}: {', '.join(issues)}"
    return f"{name}: comfort metrics outside acceptable range"
