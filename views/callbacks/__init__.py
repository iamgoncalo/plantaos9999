"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from dash_iconify import DashIconify
from loguru import logger

from views.callbacks.admin_cb import register_admin_callbacks
from views.callbacks.booking_cb import register_booking_callbacks
from views.callbacks.building_3d_cb import register_3d_callbacks
from views.callbacks.comfort_cb import register_comfort_callbacks
from views.callbacks.deployment_cb import register_deployment_callbacks
from views.callbacks.energy_cb import register_energy_callbacks
from views.callbacks.insights_cb import register_insights_callbacks
from views.callbacks.occupancy_cb import register_occupancy_callbacks
from views.callbacks.reports_cb import register_reports_callbacks
from views.callbacks.simulation_cb import register_simulation_callbacks
from views.callbacks.view_2d_cb import register_view_2d_callbacks


# Page title mapping: pathname → display title
_PAGE_TITLES: dict[str, str] = {
    "/": "Overview",
    "/overview": "Overview",
    "/energy": "Energy",
    "/comfort": "Comfort",
    "/occupancy": "Occupancy",
    "/insights": "Insights",
    "/building_3d": "3D Building",
    "/view_2d": "2D Map",
    "/view_4d": "4D Simulation",
    "/simulation": "Simulation",
    "/reports": "Reports",
    "/deployment": "Deployment",
    "/booking": "Smart Booking",
    "/admin": "Settings",
}


def register_callbacks(app: object) -> None:
    """Register all dashboard callbacks with the Dash app.

    Args:
        app: The Dash application instance.
    """
    _register_routing_callback(app)
    _register_clientside_clock(app)
    _register_building_state_callback(app)
    _register_overview_kpi_callback(app)
    _register_floorplan_callback(app)
    _register_clientside_floor_tab(app)
    _register_zone_click_callback(app)
    _register_alert_feed_callback(app)
    _register_clientside_header_status(app)
    _register_clientside_sidebar_toggle(app)
    _register_tenant_sync(app)
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
    register_booking_callbacks(app)
    register_admin_callbacks(app)


def _register_routing_callback(app: object) -> None:
    """Register the URL routing callback."""

    @app.callback(
        Output("page-content", "children"),
        Output("header-title", "children"),
        Input("url", "pathname"),
    )
    def route_page(pathname: str) -> tuple:
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

            page_map = {
                "/": create_overview_page,
                "/overview": create_overview_page,
                "/energy": create_energy_page,
                "/comfort": create_comfort_page,
                "/occupancy": create_occupancy_page,
                "/insights": create_insights_page,
                "/building_3d": create_building_3d_page,
                "/view_2d": create_view_2d_page,
                "/view_4d": create_simulation_page,
                "/simulation": create_simulation_page,
                "/reports": create_reports_page,
                "/deployment": create_deployment_page,
                "/booking": create_booking_page,
                "/admin": create_admin_page,
            }

            title = _PAGE_TITLES.get(pathname, "Not Found")
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
                            "404 — Page Not Found",
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


def _register_clientside_clock(app: object) -> None:
    """Clientside callback for header clock + shift indicator."""
    app.clientside_callback(
        """
        function(n) {
            var now = new Date();
            var h = String(now.getHours()).padStart(2, '0');
            var m = String(now.getMinutes()).padStart(2, '0');
            var s = String(now.getSeconds()).padStart(2, '0');
            var clock = h + ':' + m + ':' + s;
            var hour = now.getHours();
            var shift;
            if (hour >= 6 && hour < 14) shift = 'Morning Shift';
            else if (hour >= 14 && hour < 22) shift = 'Afternoon Shift';
            else shift = 'Off Hours';
            return [clock, shift];
        }
        """,
        Output("header-clock", "children"),
        Output("header-shift", "children"),
        Input("data-refresh-interval", "n_intervals"),
    )


def _register_building_state_callback(app: object) -> None:
    """Refresh building state every interval tick."""

    @app.callback(
        Output("building-state-store", "data"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def refresh_building_state(_n: int) -> dict:
        """Compute and store building state."""
        try:
            from core.spatial_kernel import compute_building_state

            state = compute_building_state()
            return state.model_dump(mode="json")
        except Exception as e:
            logger.warning(f"Building state refresh error: {e}")
            return no_update


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

        _empty = [
            create_kpi_card("Total Energy", "—", icon="mdi:flash"),
            create_kpi_card("Operating Cost", "—", icon="mdi:currency-eur"),
            create_kpi_card("Occupancy", "—", icon="mdi:account-group"),
            create_kpi_card("Active Alerts", "—", icon="mdi:alert-circle-outline"),
            create_kpi_card("Building Health", "—", icon="mdi:shield-check-outline"),
        ]

        if not state_data:
            return _empty

        try:
            energy = state_data.get("total_energy_kwh", 0) or 0
            occupancy = state_data.get("total_occupancy", 0) or 0
            alerts = state_data.get("active_alerts", 0) or 0

            # AFI data from spatial kernel
            total_bleed = state_data.get("total_financial_bleed_eur_hr", 0) or 0
            afi_freedom = state_data.get("avg_afi_freedom", 0) or 0
            # Fallback to legacy freedom index if AFI not computed
            if afi_freedom == 0:
                afi_freedom = state_data.get("avg_freedom_index", 0) or 0

            return [
                create_kpi_card(
                    "Total Energy",
                    format_energy(energy),
                    icon="mdi:flash",
                ),
                create_kpi_card(
                    "Operating Cost",
                    f"{total_bleed:.2f}" if total_bleed < 100 else f"{total_bleed:.0f}",
                    unit="€/hr",
                    icon="mdi:currency-eur",
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
                    f"{afi_freedom:.0f}",
                    unit="/100",
                    icon="mdi:shield-check-outline",
                ),
            ]
        except Exception as e:
            logger.warning(f"Overview KPI callback error: {e}")
            return _empty


def _register_floorplan_callback(app: object) -> None:
    """Update floorplan figure from building state and active floor."""

    @app.callback(
        Output("floorplan-graph", "figure"),
        Input("building-state-store", "data"),
        Input("active-floor-store", "data"),
    )
    def update_floorplan(state_data: dict | None, active_floor: int | None):
        """Re-render floorplan with current zone data."""
        try:
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
        except Exception as e:
            logger.warning(f"Floorplan callback error: {e}")
            return no_update


def _register_clientside_floor_tab(app: object) -> None:
    """Clientside callback for floor tab switching."""
    app.clientside_callback(
        """
        function(n0, n1) {
            var ctx = window.dash_clientside.callback_context;
            if (!ctx.triggered.length) return [0, 'floor-tab active', 'floor-tab'];
            var id = ctx.triggered[0].prop_id.split('.')[0];
            if (id === 'floor-tab-1') {
                return [1, 'floor-tab', 'floor-tab active'];
            }
            return [0, 'floor-tab active', 'floor-tab'];
        }
        """,
        Output("active-floor-store", "data"),
        Output("floor-tab-0", "className"),
        Output("floor-tab-1", "className"),
        Input("floor-tab-0", "n_clicks"),
        Input("floor-tab-1", "n_clicks"),
    )


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
        _empty = [
            html.Div(
                "Click a zone on the floorplan to see details",
                className="empty-state",
            )
        ]

        if not click_data or not state_data:
            return _empty

        try:
            from views.components.zone_panel import create_zone_detail

            # Extract zone_id from clickData
            points = click_data.get("points", [])
            zone_id = None
            for point in points:
                cd = point.get("customdata")
                if cd:
                    zone_id = cd if isinstance(cd, str) else cd[0] if cd else None
                    break

            if not zone_id:
                return _empty

            # Find zone state data
            zone_state = None
            for floor_state in state_data.get("floors", []):
                for z in floor_state.get("zones", []):
                    if z.get("zone_id") == zone_id:
                        zone_state = z
                        break

            return [create_zone_detail(zone_id=zone_id, zone_state=zone_state)]
        except Exception as e:
            logger.warning(f"Zone click callback error: {e}")
            return _empty


def _register_alert_feed_callback(app: object) -> None:
    """Update alert feed from building state."""

    @app.callback(
        Output("overview-alert-feed", "children"),
        Input("building-state-store", "data"),
    )
    def update_alert_feed(state_data: dict | None):
        """Generate alerts from zones with warning/critical status."""
        from views.components.alert_feed import create_alert_feed

        if not state_data:
            return create_alert_feed()

        try:
            from config.building import get_zone_by_id

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
        except Exception as e:
            logger.warning(f"Alert feed callback error: {e}")
            return create_alert_feed()


def _register_clientside_header_status(app: object) -> None:
    """Clientside callback for header alert count and status badge."""
    app.clientside_callback(
        """
        function(stateData) {
            if (!stateData) return ['0', 'status-badge healthy'];
            var alerts = stateData.active_alerts || 0;
            var badge;
            if (alerts > 5) badge = 'status-badge critical';
            else if (alerts > 0) badge = 'status-badge warning';
            else badge = 'status-badge healthy';
            return [String(alerts), badge];
        }
        """,
        Output("header-alert-count", "children"),
        Output("header-status", "className"),
        Input("building-state-store", "data"),
    )


def _register_clientside_sidebar_toggle(app: object) -> None:
    """Clientside callback for mobile sidebar toggle."""
    app.clientside_callback(
        """
        function(nBtn, nOverlay) {
            var sidebar = document.getElementById('sidebar');
            var overlay = document.getElementById('sidebar-overlay');
            if (!sidebar) return window.dash_clientside.no_update;
            var isOpen = sidebar.classList.contains('open');
            if (isOpen) {
                sidebar.classList.remove('open');
                if (overlay) overlay.classList.remove('active');
            } else {
                sidebar.classList.add('open');
                if (overlay) overlay.classList.add('active');
            }
            return !isOpen;
        }
        """,
        Output("sidebar-open-store", "data"),
        Input("sidebar-toggle-btn", "n_clicks"),
        Input("sidebar-overlay", "n_clicks"),
    )


def _register_tenant_sync(app: object) -> None:
    """Sync tenant dropdown selection to the tenant store."""
    app.clientside_callback(
        "function(val) { return val; }",
        Output("tenant-store", "data"),
        Input("tenant-selector", "value"),
    )


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
