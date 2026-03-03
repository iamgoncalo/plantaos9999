"""Callbacks for the standalone 2D floorplan view page.

Wires building-state-store, metric selector, and floor selector
to the 2D floorplan graph. Lazy-loads: skips regeneration when
the user is not on the /view_2d page.
"""

from __future__ import annotations

from dash import Input, Output, State, no_update
from loguru import logger

from views.floorplan.renderer_2d import render_floorplan_2d


def register_view_2d_callbacks(app: object) -> None:
    """Register all 2D floorplan view callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_floorplan_update(app)


def _register_floorplan_update(app: object) -> None:
    """Update the 2D floorplan when state, metric, or floor changes."""

    @app.callback(
        Output("view2d-floorplan-graph", "figure"),
        Input("building-state-store", "data"),
        Input("view2d-metric-selector", "value"),
        Input("view2d-floor-selector", "value"),
        State("url", "pathname"),
    )
    def update_view_2d_floorplan(
        state_data: dict | None,
        metric: str | None,
        floor_value: str | None,
        pathname: str | None,
    ) -> object:
        """Regenerate the 2D floorplan from current building state.

        Args:
            state_data: Serialized BuildingState dict from the store.
            metric: Selected metric for zone coloring.
            floor_value: Selected floor as string ("0" or "1").
            pathname: Current URL pathname for lazy-load guard.

        Returns:
            Plotly Figure with the rendered floorplan, or no_update
            when the user is not on the 2D view page.
        """
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
            )
        except Exception as e:
            logger.warning(f"2D floorplan view callback error: {e}")
            return no_update
