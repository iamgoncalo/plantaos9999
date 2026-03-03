"""Clock, sidebar, search, notification, tenant, and language callbacks."""

from __future__ import annotations

from dash import Input, Output, State, dcc, html, no_update
from dash_iconify import DashIconify

from views.components.safe_callback import safe_callback


def register_nav_callbacks(app: object) -> None:
    """Register navigation-related callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_clientside_clock(app)
    _register_clientside_sidebar_toggle(app)
    _register_sidebar_active(app)
    _register_view_submenu_toggle(app)
    _register_tenant_confirmation(app)
    _register_search_callback(app)
    _register_notification_dropdown(app)
    _register_lang_selector(app)


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


def _register_clientside_sidebar_toggle(
    app: object,
) -> None:
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
    """Clientside callback to highlight active sidebar nav item."""
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
                '/view_flow': 'view_flow', '/view_heatmap': 'view_heatmap',
                '/view_map': 'view_map'
            };
            var activeId = map[pathname] || 'overview';
            var viewSubs = ['view_2d', 'building_3d', 'building_3d_walk', 'view_4d', 'view_sensors', 'view_emergency', 'view_data', 'view_flow', 'view_heatmap', 'view_map'];
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
        Output(
            "sidebar-open-store",
            "data",
            allow_duplicate=True,
        ),
        Input("url", "pathname"),
        prevent_initial_call=True,
    )


def _register_view_submenu_toggle(app: object) -> None:
    """Clientside callback to expand/collapse View submenu."""
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
        Output(
            "sidebar-open-store",
            "data",
            allow_duplicate=True,
        ),
        Input("nav-view", "n_clicks"),
        prevent_initial_call=True,
    )


def _register_tenant_confirmation(app: object) -> None:
    """Register tenant switch with confirmation dialog.

    Step A: tenant-selector change -> store pending + show confirm
    Step B: confirm -> copy pending to tenant-store
    Step C: cancel -> revert tenant-selector
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
        """Store pending tenant and show confirmation."""
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
        """Copy pending tenant to tenant-store."""
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
        """Revert tenant-selector on cancel."""
        if not cancel_n:
            return no_update
        return current_tenant or "horse_renault"


def _register_search_callback(app: object) -> None:
    """Server-side search with results dropdown."""
    from config.building import get_monitored_zones
    from views.callbacks import _PAGE_TITLES

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
                "href": f"/view_2d?zone={zone.id}",
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
    def update_search_results(
        query: str | None,
    ) -> tuple:
        """Return matching search results."""
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


def _register_notification_dropdown(
    app: object,
) -> None:
    """Toggle notification dropdown and populate alerts."""

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
        """Toggle dropdown and populate alerts."""
        from views.callbacks.state_cb import (
            build_alert_message,
        )

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
                    if status in (
                        "warning",
                        "critical",
                    ):
                        zone_info = get_zone_by_id(zone["zone_id"])
                        name = zone_info.name if zone_info else zone["zone_id"]
                        msg = build_alert_message(zone, name)
                        severity = "critical" if status == "critical" else "warning"
                        alerts.append(
                            {
                                "message": msg,
                                "severity": severity,
                                "zone_id": zone["zone_id"],
                            }
                        )

        if not alerts:
            children = [
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:check-circle-outline",
                            width=24,
                            color="#34C759",
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
                    style={
                        "textAlign": "center",
                        "padding": "24px 16px",
                    },
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
                        "borderBottom": ("1px solid #E5E5EA"),
                    },
                )
            ]
            for alert in alerts[:20]:
                sev = alert["severity"]
                dot_color = "#FF3B30" if sev == "critical" else "#FF9500"
                children.append(
                    dcc.Link(
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
                                    style={
                                        "fontSize": "13px",
                                        "color": "#1D1D1F",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "flex-start",
                                "gap": "8px",
                                "padding": "10px 16px",
                                "borderBottom": ("1px solid #F2F2F7"),
                                "cursor": "pointer",
                            },
                        ),
                        href=f"/view_2d?zone={alert.get('zone_id', '')}",
                        style={
                            "textDecoration": "none",
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
