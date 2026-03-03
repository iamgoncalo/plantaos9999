"""Callbacks for the standalone 2D floorplan view page.

Wires building-state-store, metric selector, and floor selector
to the 2D floorplan graph. Includes keyboard navigation (Pokemon Mode)
using arrow keys to move between zones via zone adjacency and centroids.
"""

from __future__ import annotations

import math

from dash import Input, Output, State, html, no_update
from loguru import logger

from views.components.safe_callback import safe_callback
from views.floorplan.renderer_2d import render_floorplan_2d
from views.floorplan.zones_geometry import (
    get_zone_center,
    get_zones_for_floor,
)


def register_view_2d_callbacks(app: object) -> None:
    """Register all 2D floorplan view callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_floorplan_update(app)
    _register_keyboard_nav(app)
    _register_zone_detail(app)


def _register_floorplan_update(app: object) -> None:
    """Update the 2D floorplan when state, metric, floor, or selection changes."""

    @app.callback(
        Output("view2d-floorplan-graph", "figure"),
        Input("building-state-store", "data"),
        Input("view2d-metric-selector", "value"),
        Input("view2d-floor-selector", "value"),
        Input("view2d-selected-zone", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_view_2d_floorplan(
        state_data: dict | None,
        metric: str | None,
        floor_value: str | None,
        selected_zone: str | None,
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
            )
        except Exception as e:
            logger.warning(f"2D floorplan view callback error: {e}")
            return no_update


def _register_keyboard_nav(app: object) -> None:
    """Keyboard navigation: arrow keys + click to select/move between zones."""

    # Clientside callback for capturing keyboard events
    app.clientside_callback(
        """
        function(n) {
            // Set up keyboard listener on mount
            if (!window._view2dKeyHandler) {
                window._view2dKeyHandler = function(e) {
                    var keyMap = {
                        'ArrowUp': 'up', 'ArrowDown': 'down',
                        'ArrowLeft': 'left', 'ArrowRight': 'right',
                        'w': 'up', 's': 'down', 'a': 'left', 'd': 'right'
                    };
                    var dir = keyMap[e.key];
                    if (dir) {
                        e.preventDefault();
                        var store = document.getElementById('view2d-keyboard-event');
                        if (store && store._dashprivate_value !== undefined) {
                            // Trigger via store update
                        }
                        window._view2dLastKey = dir;
                        window._view2dKeyTs = Date.now();
                        // Force dash callback by updating store
                        var el = document.querySelector('[data-dash-is-loading]');
                    }
                };
                document.addEventListener('keydown', window._view2dKeyHandler);
            }
            // Return current key event
            if (window._view2dLastKey && window._view2dKeyTs) {
                var result = {direction: window._view2dLastKey, ts: window._view2dKeyTs};
                window._view2dLastKey = null;
                return result;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("view2d-keyboard-event", "data"),
        Input("data-refresh-interval", "n_intervals"),
    )

    @app.callback(
        Output("view2d-selected-zone", "data"),
        Input("view2d-keyboard-event", "data"),
        Input("view2d-floorplan-graph", "clickData"),
        State("view2d-selected-zone", "data"),
        State("view2d-floor-selector", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def navigate_zone(
        key_event: dict | None,
        click_data: dict | None,
        current_zone: str | None,
        floor_value: str | None,
        pathname: str | None,
    ) -> str | None:
        """Move zone selection based on keyboard or click events."""
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

        # Handle keyboard navigation
        if triggered == "view2d-keyboard-event" and key_event:
            direction = key_event.get("direction")
            if not direction:
                return no_update

            floor = int(floor_value) if floor_value is not None else 0
            zones = get_zones_for_floor(floor)
            zone_ids = [z.id for z in zones if z.capacity > 0]

            if not zone_ids:
                return no_update

            # If no zone selected, pick the first one
            if not current_zone or current_zone not in zone_ids:
                return zone_ids[0]

            # Find nearest zone in the given direction
            cx, cy = get_zone_center(current_zone)
            best_id = None
            best_dist = float("inf")

            for zid in zone_ids:
                if zid == current_zone:
                    continue
                zx, zy = get_zone_center(zid)
                dx = zx - cx
                dy = zy - cy

                # Check direction match
                match = False
                if direction == "right" and dx > 0.5:
                    match = True
                elif direction == "left" and dx < -0.5:
                    match = True
                elif direction == "up" and dy > 0.5:
                    match = True
                elif direction == "down" and dy < -0.5:
                    match = True

                if match:
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < best_dist:
                        best_dist = dist
                        best_id = zid

            return best_id if best_id else no_update

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
                    "CO₂",
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
