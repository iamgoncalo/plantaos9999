"""Callbacks for the 4D Time Explorer page.

Handles playback control (play/pause, speed, auto-advance), temporal
floorplan rendering at each time step, and KPI metric strip updates.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from loguru import logger

from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback


def register_view_4d_callbacks(app: object) -> None:
    """Register all 4D Time Explorer callbacks.

    Args:
        app: The Dash application instance.
    """
    logger.debug("Registering 4D Time Explorer callbacks")
    _register_play_pause(app)
    _register_speed_change(app)
    _register_auto_advance(app)
    _register_floorplan_render(app)


# ═══════════════════════════════════════════════
# Callback 1: Play / Pause toggle
# ═══════════════════════════════════════════════


def _register_play_pause(app: object) -> None:
    """Toggle playback state and enable/disable the interval timer."""

    @app.callback(
        Output("view4d-playing", "data"),
        Output("view4d-play-interval", "disabled"),
        Input("view4d-play-btn", "n_clicks"),
        State("view4d-playing", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def toggle_play_pause(
        n_clicks: int | None,
        is_playing: bool,
    ) -> tuple[bool, bool]:
        """Toggle between play and pause states.

        Args:
            n_clicks: Number of times the play button was clicked.
            is_playing: Current playback state.

        Returns:
            Tuple of (new playing state, interval disabled flag).
        """
        new_state = not is_playing
        return new_state, not new_state


# ═══════════════════════════════════════════════
# Callback 2: Speed change (clientside)
# ═══════════════════════════════════════════════


def _register_speed_change(app: object) -> None:
    """Map speed labels to interval durations via clientside callback."""

    app.clientside_callback(
        """
        function(speed) {
            var map = {"1x": 1000, "2x": 500, "5x": 200, "10x": 100};
            return map[speed] || 500;
        }
        """,
        Output("view4d-play-interval", "interval"),
        Input("view4d-speed", "value"),
    )


# ═══════════════════════════════════════════════
# Callback 3: Auto-advance slider
# ═══════════════════════════════════════════════


def _register_auto_advance(app: object) -> None:
    """Increment the time slider on each interval tick during playback."""

    @app.callback(
        Output("view4d-time-slider", "value"),
        Input("view4d-play-interval", "n_intervals"),
        State("view4d-time-slider", "value"),
        State("view4d-playing", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def auto_advance_slider(
        n_intervals: int,
        current_value: int,
        is_playing: bool,
        pathname: str | None,
    ) -> int:
        """Advance the time slider by one step when playing.

        Args:
            n_intervals: Interval tick count (triggers callback).
            current_value: Current slider position (0-2879).
            is_playing: Whether playback is active.
            pathname: Current URL pathname for lazy-load guard.

        Returns:
            New slider value, or no_update if not playing.
        """
        if not is_playing or pathname != "/view_4d":
            return no_update

        next_value = current_value + 1
        if next_value > 2879:
            next_value = 0
        return next_value


# ═══════════════════════════════════════════════
# Callback 4: Main floorplan render + KPI strip
# ═══════════════════════════════════════════════


def _register_floorplan_render(app: object) -> None:
    """Render floorplan and metric strip for the selected time step."""

    @app.callback(
        Output("view4d-floorplan", "figure"),
        Output("view4d-metric-strip", "children"),
        Output("view4d-timestamp-display", "children"),
        Input("view4d-time-slider", "value"),
        Input("view4d-metric", "value"),
        Input("view4d-floor", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def render_4d_floorplan(
        slider_val: int,
        metric: str | None,
        floor_value: str | None,
        pathname: str | None,
    ) -> tuple[go.Figure, list, str]:
        """Render the floorplan and KPI strip for a specific timestamp.

        Args:
            slider_val: Time slider position (0-2879), each step = 15 min.
            metric: Selected metric for zone coloring.
            floor_value: Selected floor as string ("0" or "1").
            pathname: Current URL pathname for lazy-load guard.

        Returns:
            Tuple of (Plotly Figure, KPI card list, timestamp string),
            or no_update triple when not on the 4D page.
        """
        if pathname != "/view_4d":
            return no_update, no_update, no_update

        from data.store import store
        from views.floorplan.renderer_2d import render_floorplan_2d

        metric = metric or "temperature_c"
        floor = int(floor_value) if floor_value is not None else 0

        # Convert slider position to timestamp
        # 2880 steps = 30 days * 96 steps/day (15-min intervals)
        base = pd.Timestamp.now().normalize() - pd.Timedelta(days=29)
        ts = base + pd.Timedelta(minutes=slider_val * 15)

        # Round to nearest 15-min boundary
        ts_rounded = ts.floor("15min")

        # ── Query data at this timestamp ───────
        comfort_df = store.get("comfort")
        energy_df = store.get("energy")
        occupancy_df = store.get("occupancy")

        zone_data: dict[str, dict] = {}

        # Comfort data (5-min intervals — find nearest to our 15-min ts)
        if not comfort_df.empty and "timestamp" in comfort_df.columns:
            comfort_ts = comfort_df["timestamp"]
            if hasattr(comfort_ts.dtype, "tz") and comfort_ts.dtype.tz is not None:
                ts_query = pd.Timestamp(ts_rounded, tz="UTC")
            else:
                ts_query = ts_rounded

            time_diffs = (comfort_df["timestamp"] - ts_query).abs()
            nearest_mask = time_diffs <= pd.Timedelta(minutes=10)
            comfort_slice = comfort_df[nearest_mask]

            for _, row in comfort_slice.iterrows():
                zid = row.get("zone_id", "")
                if zid:
                    zone_data.setdefault(zid, {})
                    zone_data[zid]["temperature_c"] = row.get("temperature_c")
                    zone_data[zid]["humidity_pct"] = row.get("humidity_pct")
                    zone_data[zid]["co2_ppm"] = row.get("co2_ppm")
                    zone_data[zid]["illuminance_lux"] = row.get("illuminance_lux")

        # Energy data (15-min intervals)
        if not energy_df.empty and "timestamp" in energy_df.columns:
            energy_ts = energy_df["timestamp"]
            if hasattr(energy_ts.dtype, "tz") and energy_ts.dtype.tz is not None:
                ts_query_e = pd.Timestamp(ts_rounded, tz="UTC")
            else:
                ts_query_e = ts_rounded

            time_diffs_e = (energy_df["timestamp"] - ts_query_e).abs()
            nearest_mask_e = time_diffs_e <= pd.Timedelta(minutes=15)
            energy_slice = energy_df[nearest_mask_e]

            for _, row in energy_slice.iterrows():
                zid = row.get("zone_id", "")
                if zid:
                    zone_data.setdefault(zid, {})
                    zone_data[zid]["total_energy_kwh"] = row.get("total_kwh", 0)

        # Occupancy data (5-min intervals)
        if not occupancy_df.empty and "timestamp" in occupancy_df.columns:
            occ_ts = occupancy_df["timestamp"]
            if hasattr(occ_ts.dtype, "tz") and occ_ts.dtype.tz is not None:
                ts_query_o = pd.Timestamp(ts_rounded, tz="UTC")
            else:
                ts_query_o = ts_rounded

            time_diffs_o = (occupancy_df["timestamp"] - ts_query_o).abs()
            nearest_mask_o = time_diffs_o <= pd.Timedelta(minutes=10)
            occ_slice = occupancy_df[nearest_mask_o]

            for _, row in occ_slice.iterrows():
                zid = row.get("zone_id", "")
                if zid:
                    zone_data.setdefault(zid, {})
                    zone_data[zid]["occupant_count"] = int(row.get("occupant_count", 0))

        # Fill defaults and compute simple freedom index estimate
        for zid in zone_data:
            zone_data[zid].setdefault("freedom_index", 50)
            zone_data[zid].setdefault("temperature_c", None)
            zone_data[zid].setdefault("humidity_pct", None)
            zone_data[zid].setdefault("co2_ppm", None)
            zone_data[zid].setdefault("illuminance_lux", None)
            zone_data[zid].setdefault("occupant_count", 0)
            zone_data[zid].setdefault("total_energy_kwh", 0)
            zone_data[zid].setdefault("status", "normal")

            # Simple freedom index heuristic from available data
            temp = zone_data[zid].get("temperature_c")
            co2 = zone_data[zid].get("co2_ppm")
            fi = 70.0
            if temp is not None:
                temp_dev = abs(temp - 22.0)
                fi -= min(temp_dev * 3, 30)
            if co2 is not None:
                co2_dev = max(0, co2 - 600) / 20
                fi -= min(co2_dev, 25)
            zone_data[zid]["freedom_index"] = round(max(0, min(100, fi)), 1)

        # ── Render floorplan ───────────────────
        fig = render_floorplan_2d(
            floor=floor,
            zone_data=zone_data,
            metric=metric,
        )

        # ── Build KPI strip ────────────────────
        temps = [
            v["temperature_c"]
            for v in zone_data.values()
            if v.get("temperature_c") is not None
        ]
        co2s = [
            v["co2_ppm"] for v in zone_data.values() if v.get("co2_ppm") is not None
        ]
        energies = [v.get("total_energy_kwh", 0) for v in zone_data.values()]
        occupants = [v.get("occupant_count", 0) for v in zone_data.values()]

        avg_temp = sum(temps) / len(temps) if temps else 0
        avg_co2 = sum(co2s) / len(co2s) if co2s else 0
        total_energy = sum(energies)
        total_occ = sum(occupants)

        kpi_cards = [
            create_kpi_card(
                title="Avg Temperature",
                value=f"{avg_temp:.1f}",
                unit="\u00b0C",
                icon="mdi:thermometer",
            ),
            create_kpi_card(
                title="Avg CO2",
                value=f"{avg_co2:.0f}",
                unit="ppm",
                icon="mdi:molecule-co2",
            ),
            create_kpi_card(
                title="Total Energy",
                value=f"{total_energy:.2f}",
                unit="kWh",
                icon="mdi:lightning-bolt",
            ),
            create_kpi_card(
                title="Occupants",
                value=f"{total_occ}",
                icon="mdi:account-group",
            ),
        ]

        # ── Timestamp display ──────────────────
        ts_label = html.Span(ts.strftime("%a %d %b %Y  %H:%M"))

        return fig, kpi_cards, ts_label
