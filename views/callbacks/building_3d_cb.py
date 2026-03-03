"""Callbacks for the 3D building view page.

Wires building-state-store, metric selector, and floor selector
to the Three.js iframe srcdoc via generate_3d_html().
Lazy-loads: skips regeneration when user is not on the 3D page.
"""

from __future__ import annotations

from dash import Input, Output, State, no_update
from loguru import logger
from views.components.safe_callback import safe_callback


def register_3d_callbacks(app: object) -> None:
    """Register all 3D building view callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_3d_update(app)
    _register_3d_fp_toggle(app)
    _register_3d_reset_camera(app)
    _register_3d_teleport(app)


def _register_3d_update(app: object) -> None:
    """Update the 3D iframe when state, metric, or floor changes."""

    @app.callback(
        Output("3d-viewer-iframe", "srcDoc"),
        Input("building-state-store", "data"),
        Input("3d-metric-selector", "value"),
        Input("3d-floor-selector", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_3d_view(
        state_data: dict | None,
        metric: str | None,
        visible_floors: str | None,
        pathname: str | None,
    ) -> str:
        """Regenerate 3D HTML from current building state.

        Args:
            state_data: Serialized BuildingState dict.
            metric: Selected metric for zone coloring.
            visible_floors: Which floors to show.
            pathname: Current URL pathname for lazy-load check.

        Returns:
            HTML string for the iframe srcdoc.
        """
        # Lazy-load: skip expensive 3D generation when not on 3D page
        if pathname != "/building_3d":
            return no_update

        try:
            from views.floorplan.renderer_3d import generate_3d_html

            metric = metric or "freedom_index"
            visible_floors = visible_floors or "all"

            # Extract zone data and AFI data from building state
            zone_data: dict = {}
            afi_data: dict = {}
            if state_data:
                for floor_state in state_data.get("floors", []):
                    for zone in floor_state.get("zones", []):
                        zid = zone["zone_id"]
                        zone_data[zid] = {
                            "freedom_index": zone.get("freedom_index", 50),
                            "temperature_c": zone.get("temperature_c"),
                            "humidity_pct": zone.get("humidity_pct"),
                            "co2_ppm": zone.get("co2_ppm"),
                            "occupant_count": zone.get("occupant_count", 0),
                            "total_energy_kwh": zone.get("total_energy_kwh", 0),
                            "status": zone.get("status", "unknown"),
                        }
                        # AFI overlay data
                        bleed = zone.get("financial_bleed_eur_hr", 0)
                        freedom = zone.get("afi_freedom", 0)
                        if bleed or freedom:
                            afi_data[zid] = {
                                "financial_bleed_eur_hr": bleed,
                                "freedom": freedom,
                                "perception": zone.get("perception", 0),
                                "distortion": zone.get("distortion", 1),
                            }

            return generate_3d_html(
                building_data=zone_data,
                metric=metric,
                visible_floors=visible_floors,
                afi_data=afi_data if afi_data else None,
            )
        except Exception as e:
            logger.warning(f"3D view callback error: {e}")
            return no_update


def _register_3d_fp_toggle(app: object) -> None:
    """Send first-person mode postMessage to 3D iframe."""

    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            var iframe = document.getElementById("3d-viewer-iframe");
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage(
                    {type: "set-mode", mode: "walk"}, "*"
                );
            }
            return "";
        }
        """,
        Output("3d-fp-btn", "title"),
        Input("3d-fp-btn", "n_clicks"),
        prevent_initial_call=True,
    )


def _register_3d_reset_camera(app: object) -> None:
    """Send reset-camera postMessage to 3D iframe."""

    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            var iframe = document.getElementById("3d-viewer-iframe");
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage(
                    {type: "reset-camera"}, "*"
                );
            }
            return "";
        }
        """,
        Output("3d-reset-camera-btn", "title"),
        Input("3d-reset-camera-btn", "n_clicks"),
        prevent_initial_call=True,
    )


def _register_3d_teleport(app: object) -> None:
    """Send teleport postMessage to 3D iframe when zone selected."""

    app.clientside_callback(
        """
        function(value) {
            if (!value) return window.dash_clientside.no_update;
            var iframe = document.getElementById("3d-viewer-iframe");
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage(
                    {type: "teleport", zoneId: value}, "*"
                );
            }
            return "";
        }
        """,
        Output("3d-teleport-dropdown", "title"),
        Input("3d-teleport-dropdown", "value"),
        prevent_initial_call=True,
    )
