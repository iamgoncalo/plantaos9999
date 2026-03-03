"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations

from dash import Input, Output, State, dcc, html, no_update
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
from views.callbacks.occupancy_cb import register_occupancy_callbacks
from views.callbacks.reports_cb import register_reports_callbacks
from views.callbacks.simulation_cb import register_simulation_callbacks
from views.callbacks.view_2d_cb import register_view_2d_callbacks
from views.callbacks.view_4d_cb import register_view_4d_callbacks
from views.callbacks.view_data_cb import register_data_explorer_callbacks
from views.callbacks.view_emergency_cb import register_emergency_callbacks
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


# Page title mapping: pathname → display title
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
    _register_sidebar_active(app)
    _register_view_submenu_toggle(app)
    _register_tenant_confirmation(app)
    _register_search_callback(app)
    _register_notification_dropdown(app)
    _register_lang_selector(app)
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
    # Optional callback modules (created by other agents)
    if register_sensors_callbacks is not None:
        register_sensors_callbacks(app)
    if register_flow_callbacks is not None:
        register_flow_callbacks(app)
    if register_heatmap_callbacks is not None:
        register_heatmap_callbacks(app)


def _register_routing_callback(app: object) -> None:
    """Register the URL routing callback."""

    @app.callback(
        Output("page-content", "children"),
        Output("header-title", "children"),
        Input("url", "pathname"),
    )
    @safe_callback
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
            from views.pages.view_4d import create_view_4d_page
            from views.pages.view_data import create_data_explorer_page
            from views.pages.view_emergency import create_emergency_page
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
            }

            # Add optional pages if available
            if create_sensors_page is not None:
                page_map["/sensors"] = create_sensors_page
            if create_flow_page is not None:
                page_map["/view_flow"] = create_flow_page
            if create_heatmap_page is not None:
                page_map["/view_heatmap"] = create_heatmap_page

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
    """Clientside callback for header clock + shift indicator.

    Sets up a JS setInterval(1000) on first trigger so the clock
    ticks every second independently of the 5s data-refresh-interval.
    """
    app.clientside_callback(
        """
        function(n) {
            if (!window._plantaClockInterval) {
                window._plantaClockInterval = setInterval(function() {
                    var now = new Date();
                    var h = String(now.getHours()).padStart(2, '0');
                    var m = String(now.getMinutes()).padStart(2, '0');
                    var s = String(now.getSeconds()).padStart(2, '0');
                    var el = document.getElementById('header-clock');
                    var sh = document.getElementById('header-shift');
                    if (el) el.textContent = h + ':' + m + ':' + s;
                    if (sh) {
                        var hr = now.getHours();
                        if (hr >= 6 && hr < 14) sh.textContent = 'Morning Shift';
                        else if (hr >= 14 && hr < 22) sh.textContent = 'Afternoon Shift';
                        else sh.textContent = 'Off Hours';
                    }
                }, 1000);
            }
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


# Tenant-specific scaling factors for demo tenants
_TENANT_SCALE: dict[str, dict] = {
    "horse_renault": {"energy": 1.0, "occ": 1.0, "label": "CFT Aveiro"},
    "airbus_assembly": {"energy": 12.5, "occ": 8.0, "label": "FAL A320"},
    "ikea_logistics": {"energy": 35.0, "occ": 15.0, "label": "DC Almeirim"},
}


def _register_building_state_callback(app: object) -> None:
    """Refresh building state every interval tick, scaled by tenant."""

    @app.callback(
        Output("building-state-store", "data"),
        Input("data-refresh-interval", "n_intervals"),
        Input("tenant-store", "data"),
    )
    @safe_callback
    def refresh_building_state(_n: int, tenant: str | None) -> dict:
        """Compute and store building state with tenant scaling."""
        try:
            from core.spatial_kernel import compute_building_state

            state = compute_building_state()
            data = state.model_dump(mode="json")

            # Apply tenant-specific scaling for demo
            scale = _TENANT_SCALE.get(tenant or "horse_renault", {})
            e_scale = scale.get("energy", 1.0)
            o_scale = scale.get("occ", 1.0)
            if e_scale != 1.0 or o_scale != 1.0:
                data["total_energy_kwh"] = round(
                    (data.get("total_energy_kwh", 0) or 0) * e_scale, 4
                )
                data["total_occupancy"] = int(
                    (data.get("total_occupancy", 0) or 0) * o_scale
                )
                bleed = data.get("total_financial_bleed_eur_hr", 0) or 0
                data["total_financial_bleed_eur_hr"] = round(bleed * e_scale, 4)
            # Attach tenant label for header display
            data["_tenant_label"] = scale.get("label", "CFT Aveiro")
            return data
        except Exception as e:
            logger.warning(f"Building state refresh error: {e}")
            return no_update


def _register_overview_kpi_callback(app: object) -> None:
    """Update overview KPI cards from building state."""

    @app.callback(
        Output("overview-kpi-grid", "children"),
        Input("building-state-store", "data"),
    )
    @safe_callback
    def update_kpis(state_data: dict | None) -> list:
        """Regenerate KPI cards with live data."""
        from utils.formatters import format_energy
        from views.components.kpi_card import create_kpi_card

        _empty = [
            create_kpi_card("Total Energy", "—", icon="mdi:flash"),
            create_kpi_card("Operating Cost", "—", icon="mdi:currency-eur"),
            create_kpi_card("Occupancy", "—", icon="mdi:account-group"),
            create_kpi_card("Active Alerts", "—", icon="mdi:alert-circle-outline"),
            create_kpi_card("Zone Performance", "—", icon="mdi:shield-check-outline"),
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
                    "Zone Performance",
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
    @safe_callback
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
    @safe_callback
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
                    if isinstance(cd, str):
                        zone_id = cd
                    elif isinstance(cd, (list, tuple)) and len(cd) > 0:
                        zone_id = cd[0]
                    else:
                        zone_id = None
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
    @safe_callback
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


def _register_sidebar_active(app: object) -> None:
    """Clientside callback to update sidebar active nav item on URL change."""
    app.clientside_callback(
        """
        function(pathname) {
            var map = {
                '/': 'overview', '/overview': 'overview',
                '/energy': 'energy', '/comfort': 'comfort',
                '/occupancy': 'occupancy', '/insights': 'insights',
                '/simulation': 'simulation', '/reports': 'reports',
                '/sensors': 'sensors', '/admin': 'admin',
                '/booking': 'booking',
                '/view_2d': 'view_2d', '/building_3d': 'building_3d',
                '/building_3d_walk': 'building_3d_walk',
                '/view_4d': 'view_4d', '/view_sensors': 'view_sensors',
                '/view_emergency': 'view_emergency', '/view_data': 'view_data',
                '/view_flow': 'view_flow', '/view_heatmap': 'view_heatmap'
            };
            var activeId = map[pathname] || 'overview';
            var viewSubs = ['view_2d', 'building_3d', 'building_3d_walk', 'view_4d', 'view_sensors', 'view_emergency', 'view_data', 'view_flow', 'view_heatmap'];
            var isViewPage = viewSubs.indexOf(activeId) >= 0;

            document.querySelectorAll('.sidebar-nav-item').forEach(function(el) {
                el.classList.remove('active');
            });
            var activeEl = document.getElementById('nav-' + activeId);
            if (activeEl) activeEl.classList.add('active');

            var viewParent = document.getElementById('nav-view');
            var submenu = document.getElementById('submenu-view');
            if (viewParent && submenu) {
                if (isViewPage) {
                    viewParent.classList.add('active');
                    submenu.style.display = 'flex';
                } else {
                    viewParent.classList.remove('active');
                    submenu.style.display = 'none';
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("sidebar-open-store", "data", allow_duplicate=True),
        Input("url", "pathname"),
        prevent_initial_call=True,
    )


def _register_view_submenu_toggle(app: object) -> None:
    """Clientside callback to expand/collapse View submenu on click."""
    app.clientside_callback(
        """
        function(n) {
            var sub = document.getElementById('submenu-view');
            if (sub) {
                var vis = sub.style.display;
                sub.style.display = (vis === 'none' || !vis) ? 'flex' : 'none';
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("sidebar-open-store", "data", allow_duplicate=True),
        Input("nav-view", "n_clicks"),
        prevent_initial_call=True,
    )


def _register_tenant_confirmation(app: object) -> None:
    """Register tenant switch with confirmation dialog.

    Step A: tenant-selector change -> store pending value + show confirm dialog
    Step B: confirm -> copy pending to tenant-store
    Step C: cancel -> revert tenant-selector to current tenant-store
    """
    _tenant_labels: dict[str, str] = {
        "horse_renault": "CFT Aveiro",
        "airbus_assembly": "FAL A320",
        "ikea_logistics": "DC Almeirim",
    }

    @app.callback(
        Output("tenant-pending-store", "data"),
        Output("tenant-confirm-dialog", "displayed"),
        Input("tenant-selector", "value"),
        State("tenant-store", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def tenant_selector_changed(
        new_val: str | None,
        current_tenant: str | None,
    ) -> tuple:
        """Store pending tenant and show confirmation dialog."""
        if not new_val or new_val == current_tenant:
            return no_update, False
        return new_val, True

    @app.callback(
        Output("tenant-store", "data"),
        Output("header-building-name", "children"),
        Input("tenant-confirm-dialog", "submit_n_clicks"),
        State("tenant-pending-store", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def tenant_confirmed(
        submit_n: int | None,
        pending: str | None,
    ) -> tuple:
        """Copy pending tenant to tenant-store on confirmation."""
        if not submit_n or not pending:
            return no_update, no_update
        label = _tenant_labels.get(pending, "CFT Aveiro")
        return pending, label

    @app.callback(
        Output("tenant-selector", "value"),
        Input("tenant-confirm-dialog", "cancel_n_clicks"),
        State("tenant-store", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def tenant_cancelled(
        cancel_n: int | None,
        current_tenant: str | None,
    ) -> str:
        """Revert tenant-selector to current tenant on cancel."""
        if not cancel_n:
            return no_update
        return current_tenant or "horse_renault"


def _register_search_callback(app: object) -> None:
    """Server-side search with results dropdown + navigation on selection."""
    from config.building import get_monitored_zones

    # Build search index once at registration time
    _search_entries: list[dict] = []

    # Pages
    for path, title in _PAGE_TITLES.items():
        if path != "/":
            _search_entries.append(
                {
                    "label": title,
                    "category": "Page",
                    "href": path,
                    "floor": None,
                }
            )

    # Zones
    for zone in get_monitored_zones():
        _search_entries.append(
            {
                "label": zone.name,
                "category": "Zone",
                "href": "/",
                "floor": zone.floor,
            }
        )

    # Metrics
    for metric in [
        "Temperature",
        "CO2",
        "Humidity",
        "Energy",
        "Occupancy",
        "Illuminance",
    ]:
        _search_entries.append(
            {
                "label": metric,
                "category": "Metric",
                "href": "/comfort"
                if metric in ("Temperature", "CO2", "Humidity")
                else "/energy"
                if metric == "Energy"
                else "/occupancy"
                if metric == "Occupancy"
                else "/comfort",
                "floor": None,
            }
        )

    @app.callback(
        Output("search-results-container", "children"),
        Output("search-results-container", "style"),
        Input("global-search-input", "value"),
        prevent_initial_call=True,
    )
    @safe_callback
    def update_search_results(query: str | None) -> tuple:
        """Return matching search results as clickable items."""
        if not query or len(query) < 2:
            return [], {"display": "none"}

        q = query.lower()
        matches = [
            e
            for e in _search_entries
            if q in e["label"].lower() or q in e["category"].lower()
        ][:8]

        if not matches:
            return [
                html.Div(
                    "No results found",
                    style={
                        "padding": "12px 16px",
                        "color": "#86868B",
                        "fontSize": "13px",
                    },
                ),
            ], {"display": "block"}

        items = []
        for m in matches:
            badge_color = {
                "Page": "#0071E3",
                "Zone": "#34C759",
                "Metric": "#FF9500",
            }.get(m["category"], "#86868B")

            items.append(
                dcc.Link(
                    html.Div(
                        [
                            html.Span(
                                m["category"],
                                style={
                                    "fontSize": "10px",
                                    "fontWeight": 600,
                                    "color": "#FFFFFF",
                                    "background": badge_color,
                                    "borderRadius": "4px",
                                    "padding": "2px 6px",
                                    "flexShrink": 0,
                                },
                            ),
                            html.Span(
                                m["label"],
                                style={
                                    "fontSize": "13px",
                                    "color": "#1D1D1F",
                                },
                            ),
                        ],
                        className="search-result-item",
                    ),
                    href=m["href"],
                )
            )

        return items, {"display": "block"}


def _register_notification_dropdown(app: object) -> None:
    """Toggle notification dropdown and populate with recent alerts."""

    @app.callback(
        Output("notification-dropdown", "children"),
        Output("notification-dropdown", "style"),
        Input("notification-bell-btn", "n_clicks"),
        State("building-state-store", "data"),
        State("notification-dropdown", "style"),
        prevent_initial_call=True,
    )
    @safe_callback
    def toggle_notification_dropdown(
        n_clicks: int | None,
        state_data: dict | None,
        current_style: dict | None,
    ) -> tuple:
        """Toggle dropdown visibility and populate alerts."""
        if not n_clicks:
            return no_update, no_update

        current_style = current_style or {}
        is_visible = current_style.get("display") != "none"

        if is_visible:
            return no_update, {"display": "none"}

        # Build alert items from building state
        from config.building import get_zone_by_id

        alerts: list = []
        if state_data:
            for floor_state in state_data.get("floors", []):
                for zone in floor_state.get("zones", []):
                    status = zone.get("status", "unknown")
                    if status in ("warning", "critical"):
                        zone_info = get_zone_by_id(zone["zone_id"])
                        name = zone_info.name if zone_info else zone["zone_id"]
                        msg = _build_alert_message(zone, name)
                        severity = "critical" if status == "critical" else "warning"
                        alerts.append({"message": msg, "severity": severity})

        if not alerts:
            children = [
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:check-circle-outline", width=24, color="#34C759"
                        ),
                        html.P(
                            "No active alerts",
                            style={
                                "margin": "8px 0 0",
                                "fontSize": "13px",
                                "color": "#6E6E73",
                            },
                        ),
                    ],
                    style={"textAlign": "center", "padding": "24px 16px"},
                )
            ]
        else:
            children = [
                html.Div(
                    "Recent Alerts",
                    style={
                        "fontSize": "13px",
                        "fontWeight": 600,
                        "padding": "12px 16px 8px",
                        "color": "#1D1D1F",
                        "borderBottom": "1px solid #E5E5EA",
                    },
                )
            ]
            for alert in alerts[:20]:
                sev = alert["severity"]
                dot_color = "#FF3B30" if sev == "critical" else "#FF9500"
                children.append(
                    html.Div(
                        [
                            html.Span(
                                style={
                                    "width": "8px",
                                    "height": "8px",
                                    "borderRadius": "50%",
                                    "background": dot_color,
                                    "flexShrink": 0,
                                },
                            ),
                            html.Span(
                                alert["message"],
                                style={"fontSize": "13px", "color": "#1D1D1F"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "flex-start",
                            "gap": "8px",
                            "padding": "10px 16px",
                            "borderBottom": "1px solid #F2F2F7",
                        },
                    )
                )

        return children, {"display": "block"}


def _register_lang_selector(app: object) -> None:
    """Sync language dropdown to lang-store."""
    app.clientside_callback(
        """
        function(val) {
            return val || 'en';
        }
        """,
        Output("lang-store", "data"),
        Input("lang-selector", "value"),
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
