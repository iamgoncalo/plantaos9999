"""Building state, KPI, floorplan, floor tab, zone click, and alert callbacks."""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from loguru import logger

from views.components.safe_callback import safe_callback

# Tenant-specific scaling factors for demo tenants
_TENANT_SCALE: dict[str, dict] = {
    "horse_renault": {
        "energy": 1.0,
        "occ": 1.0,
        "label": "CFT Aveiro",
    },
    "airbus_assembly": {
        "energy": 12.5,
        "occ": 8.0,
        "label": "FAL A320",
    },
    "ikea_logistics": {
        "energy": 35.0,
        "occ": 15.0,
        "label": "DC Almeirim",
    },
}


def build_alert_message(zone_data: dict, name: str) -> str:
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
        issues.append(f"CO\u2082 at {co2:.0f} ppm")

    temp = zone_data.get("temperature_c")
    if temp is not None and (temp > 26 or temp < 18):
        direction = "above" if temp > 26 else "below"
        issues.append(f"Temperature {direction} range ({temp:.1f} \u00b0C)")

    hum = zone_data.get("humidity_pct")
    if hum is not None and (hum > 70 or hum < 30):
        issues.append(f"Humidity at {hum:.0f}%")

    if issues:
        return f"{name}: {', '.join(issues)}"
    return f"{name}: comfort metrics outside acceptable range"


def register_state_callbacks(app: object) -> None:
    """Register building state, KPI, floorplan, and alert callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_building_state_callback(app)
    _register_overview_kpi_callback(app)
    _register_floorplan_callback(app)
    _register_clientside_floor_tab(app)
    _register_zone_click_callback(app)
    _register_alert_feed_callback(app)
    _register_clientside_header_status(app)


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
                    (data.get("total_energy_kwh", 0) or 0) * e_scale,
                    4,
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
            create_kpi_card("Total Energy", "\u2014", icon="mdi:flash"),
            create_kpi_card(
                "Operating Cost",
                "\u2014",
                icon="mdi:currency-eur",
            ),
            create_kpi_card(
                "Occupancy",
                "\u2014",
                icon="mdi:account-group",
            ),
            create_kpi_card(
                "Active Alerts",
                "\u2014",
                icon="mdi:alert-circle-outline",
            ),
            create_kpi_card(
                "Zone Performance",
                "\u2014",
                icon="mdi:shield-check-outline",
            ),
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
            # Fallback to legacy freedom index
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
                    unit="\u20ac/hr",
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
    def update_floorplan(
        state_data: dict | None,
        active_floor: int | None,
    ):
        """Re-render floorplan with current zone data."""
        try:
            from views.floorplan.renderer_2d import (
                render_floorplan_2d,
            )

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
            if (!ctx.triggered.length)
                return [0, 'floor-tab active', 'floor-tab'];
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
    """Update zone detail panel when a zone is clicked."""

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
            from views.components.zone_panel import (
                create_zone_detail,
            )

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

            return [
                create_zone_detail(
                    zone_id=zone_id,
                    zone_state=zone_state,
                )
            ]
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
        """Generate alerts from zones with warning/critical."""
        from views.components.alert_feed import (
            create_alert_feed,
        )

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

                        msg = build_alert_message(zone, name)
                        alerts.append(
                            {
                                "message": msg,
                                "severity": severity,
                                "timestamp": zone.get("timestamp", ""),
                                "zone_id": zone["zone_id"],
                            }
                        )

            # Critical alerts first
            alerts.sort(
                key=lambda a: a["severity"] == "critical",
                reverse=True,
            )
            return create_alert_feed(alerts=alerts)
        except Exception as e:
            logger.warning(f"Alert feed callback error: {e}")
            return create_alert_feed()


def _register_clientside_header_status(
    app: object,
) -> None:
    """Clientside callback for header alert count and status badge."""
    app.clientside_callback(
        """
        function(stateData) {
            if (!stateData)
                return ['0', 'status-badge healthy'];
            var alerts = stateData.active_alerts || 0;
            var badge;
            if (alerts > 5)
                badge = 'status-badge critical';
            else if (alerts > 0)
                badge = 'status-badge warning';
            else badge = 'status-badge healthy';
            return [String(alerts), badge];
        }
        """,
        Output("header-alert-count", "children"),
        Output("header-status", "className"),
        Input("building-state-store", "data"),
    )
