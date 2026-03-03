"""Callbacks for the standalone 2D floorplan view page.

Wires building-state-store, metric selector, floor selector, avatar
position, and overlay selector to the 2D floorplan graph. Includes
smooth WASD/arrow-key avatar movement with collision detection via
clientside callbacks.
"""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from loguru import logger

from core.geometry import FLOOR_0_WALKABLE, FLOOR_1_WALKABLE
from views.components.safe_callback import safe_callback
from views.floorplan.renderer_2d import render_floorplan_2d
from views.floorplan.zones_geometry import (
    get_zones_for_floor,
)


def register_view_2d_callbacks(app: object) -> None:
    """Register all 2D floorplan view callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_floorplan_update(app)
    _register_keyboard_setup(app)
    _register_key_poll(app)
    _register_walkable_update(app)
    _register_overlay_sync(app)
    _register_zone_auto_select(app)
    _register_zone_detail(app)


def _register_floorplan_update(app: object) -> None:
    """Update the 2D floorplan when state, metric, floor, selection, or avatar changes."""

    @app.callback(
        Output("view2d-floorplan-graph", "figure"),
        Input("building-state-store", "data"),
        Input("view2d-metric-selector", "value"),
        Input("view2d-floor-selector", "value"),
        Input("view2d-selected-zone", "data"),
        Input("view2d-avatar-pos", "data"),
        Input("view2d-overlays", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_view_2d_floorplan(
        state_data: dict | None,
        metric: str | None,
        floor_value: str | None,
        selected_zone: str | None,
        avatar_pos: dict | None,
        overlays: list[str] | None,
        pathname: str | None,
    ) -> object:
        """Regenerate the 2D floorplan from current building state."""
        if pathname != "/view_2d":
            return no_update

        try:
            metric = metric or "freedom_index"
            floor = int(floor_value) if floor_value is not None else 0

            # Extract zone_data from building state
            zone_data: dict = {}
            if state_data:
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
                            "financial_bleed": zone.get("financial_bleed", 0),
                            "status": zone.get("status", "unknown"),
                        }

            return render_floorplan_2d(
                floor=floor,
                zone_data=zone_data,
                metric=metric,
                selected_zone=selected_zone,
                avatar_pos=avatar_pos,
                overlays=overlays,
            )
        except Exception as e:
            logger.warning(f"2D floorplan view callback error: {e}")
            return no_update


def _register_keyboard_setup(app: object) -> None:
    """Set up keydown/keyup listeners on page load via clientside callback."""

    app.clientside_callback(
        """
        function(pathname) {
            if (pathname !== '/view_2d') return window.dash_clientside.no_update;
            if (!window._view2dKeysDown) {
                window._view2dKeysDown = {};
                document.addEventListener('keydown', function(e) {
                    var validKeys = [
                        'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
                        'KeyW', 'KeyA', 'KeyS', 'KeyD'
                    ];
                    if (validKeys.indexOf(e.code) !== -1) {
                        e.preventDefault();
                        window._view2dKeysDown[e.code] = true;
                    }
                });
                document.addEventListener('keyup', function(e) {
                    if (window._view2dKeysDown[e.code] !== undefined) {
                        delete window._view2dKeysDown[e.code];
                    }
                });
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("view2d-keyboard-event", "data"),
        Input("url", "pathname"),
    )


def _register_key_poll(app: object) -> None:
    """Poll held keys on interval and move avatar with collision check."""

    app.clientside_callback(
        """
        function(n, pos, polys) {
            var keys = window._view2dKeysDown || {};
            var x = pos.x, y = pos.y;
            var speed = 0.5;
            var moved = false;
            if (keys['ArrowUp'] || keys['KeyW']) { y += speed; moved = true; }
            if (keys['ArrowDown'] || keys['KeyS']) { y -= speed; moved = true; }
            if (keys['ArrowLeft'] || keys['KeyA']) { x -= speed; moved = true; }
            if (keys['ArrowRight'] || keys['KeyD']) { x += speed; moved = true; }
            if (!moved) return window.dash_clientside.no_update;
            function pip(px, py, poly) {
                var inside = false;
                for (var i = 0, j = poly.length - 1; i < poly.length; j = i++) {
                    var xi = poly[i][0], yi = poly[i][1];
                    var xj = poly[j][0], yj = poly[j][1];
                    if ((yi > py) !== (yj > py) &&
                        px < (xj - xi) * (py - yi) / (yj - yi) + xi)
                        inside = !inside;
                }
                return inside;
            }
            var walkable = false;
            for (var k = 0; k < polys.length; k++) {
                if (pip(x, y, polys[k])) { walkable = true; break; }
            }
            if (!walkable) return window.dash_clientside.no_update;
            return {x: x, y: y};
        }
        """,
        Output("view2d-avatar-pos", "data"),
        Input("view2d-key-poll", "n_intervals"),
        State("view2d-avatar-pos", "data"),
        State("view2d-walkable-polys", "data"),
    )


def _register_walkable_update(app: object) -> None:
    """Update walkable polygons when floor changes."""

    @app.callback(
        Output("view2d-walkable-polys", "data"),
        Input("view2d-floor-selector", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_walkable_polys(
        floor_value: str | None,
        pathname: str | None,
    ) -> object:
        """Return walkable polygons for the selected floor."""
        if pathname != "/view_2d":
            return no_update
        floor = int(floor_value) if floor_value is not None else 0
        return FLOOR_0_WALKABLE if floor == 0 else FLOOR_1_WALKABLE


def _register_overlay_sync(app: object) -> None:
    """Sync overlay selector value to overlays store."""

    app.clientside_callback(
        """
        function(value) {
            if (!value || value === 'none') return [];
            return [value];
        }
        """,
        Output("view2d-overlays", "data"),
        Input("view2d-overlay-selector", "value"),
    )


def _register_zone_auto_select(app: object) -> None:
    """Auto-select zone when avatar enters it."""

    @app.callback(
        Output("view2d-selected-zone", "data"),
        Input("view2d-avatar-pos", "data"),
        Input("view2d-floorplan-graph", "clickData"),
        State("view2d-selected-zone", "data"),
        State("view2d-floor-selector", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def auto_select_zone(
        avatar_pos: dict | None,
        click_data: dict | None,
        current_zone: str | None,
        floor_value: str | None,
        pathname: str | None,
    ) -> str | None:
        """Select zone based on avatar position or click."""
        if pathname != "/view_2d":
            return no_update

        from dash import ctx

        triggered = ctx.triggered_id

        # Handle click selection
        if triggered == "view2d-floorplan-graph" and click_data:
            points = click_data.get("points", [])
            for point in points:
                cd = point.get("customdata")
                if cd:
                    zone_id = cd if isinstance(cd, str) else cd[0] if cd else None
                    if zone_id:
                        return zone_id
            return no_update

        # Handle avatar position — find which zone the avatar is in
        if triggered == "view2d-avatar-pos" and avatar_pos:
            from core.geometry import point_in_polygon

            ax = avatar_pos.get("x", 0)
            ay = avatar_pos.get("y", 0)
            floor = int(floor_value) if floor_value is not None else 0
            zones = get_zones_for_floor(floor)

            for z in zones:
                pts = z.points
                if point_in_polygon(ax, ay, pts):
                    if z.id != current_zone:
                        return z.id
                    return no_update
            return no_update

        return no_update


def _register_zone_detail(app: object) -> None:
    """Update zone detail panel when a zone is selected."""

    @app.callback(
        Output("view2d-zone-detail-panel", "children"),
        Input("view2d-selected-zone", "data"),
        State("building-state-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_zone_detail(
        selected_zone: str | None,
        state_data: dict | None,
        pathname: str | None,
    ) -> object:
        """Show zone metrics for the selected zone."""
        if pathname != "/view_2d" or not selected_zone:
            return no_update

        from config.building import get_zone_by_id
        from config.theme import TEXT_SECONDARY, TEXT_TERTIARY
        from dash_iconify import DashIconify

        zone_info = get_zone_by_id(selected_zone)
        zone_name = zone_info.name if zone_info else selected_zone

        # Find zone state
        zone_state = None
        if state_data:
            for floor_state in state_data.get("floors", []):
                for z in floor_state.get("zones", []):
                    if z.get("zone_id") == selected_zone:
                        zone_state = z
                        break

        if not zone_state:
            return html.Div(
                [
                    html.Span(zone_name, style={"fontWeight": 600, "fontSize": "15px"}),
                    html.Span(
                        " — No data available",
                        style={"fontSize": "13px", "color": TEXT_TERTIARY},
                    ),
                ],
                style={"padding": "16px 20px"},
            )

        temp = zone_state.get("temperature_c")
        co2 = zone_state.get("co2_ppm")
        hum = zone_state.get("humidity_pct")
        occ = zone_state.get("occupant_count", 0)
        score = zone_state.get("freedom_index", 0)
        energy = zone_state.get("total_energy_kwh", 0)

        def _metric_row(icon: str, label: str, value: str) -> html.Div:
            return html.Div(
                [
                    html.Div(
                        [
                            DashIconify(icon=icon, width=16, color=TEXT_SECONDARY),
                            html.Span(
                                label,
                                style={"fontSize": "13px", "color": TEXT_SECONDARY},
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                    ),
                    html.Span(
                        value,
                        style={
                            "fontSize": "14px",
                            "fontWeight": 500,
                            "fontFamily": "'JetBrains Mono', monospace",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "padding": "8px 0",
                    "borderBottom": "1px solid #F2F2F7",
                },
            )

        return html.Div(
            [
                html.Div(
                    [
                        DashIconify(icon="mdi:map-marker", width=18, color="#0071E3"),
                        html.Span(
                            zone_name,
                            style={"fontWeight": 600, "fontSize": "15px"},
                        ),
                        html.Span(
                            f"Score: {score:.0f}/100",
                            style={
                                "fontSize": "12px",
                                "fontWeight": 500,
                                "color": "#34C759" if score >= 70 else "#FF9500",
                                "background": "#E8F9EE" if score >= 70 else "#FFF4E6",
                                "padding": "2px 8px",
                                "borderRadius": "8px",
                                "marginLeft": "auto",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "12px",
                    },
                ),
                _metric_row(
                    "mdi:thermometer",
                    "Temperature",
                    f"{temp:.1f} °C" if temp else "—",
                ),
                _metric_row(
                    "mdi:molecule-co2",
                    "CO2",
                    f"{co2:.0f} ppm" if co2 else "—",
                ),
                _metric_row(
                    "mdi:water-percent",
                    "Humidity",
                    f"{hum:.0f}%" if hum else "—",
                ),
                _metric_row(
                    "mdi:account-group",
                    "Occupancy",
                    str(occ),
                ),
                _metric_row(
                    "mdi:flash",
                    "Energy",
                    f"{energy:.2f} kWh",
                ),
            ],
            style={"padding": "16px 20px"},
        )
