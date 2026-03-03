"""Callbacks for the Sensor Coverage page.

Renders sensor positions on the 2D floorplan with coverage radii,
deployment status overlays, and battery health coloring. Also
populates the sensor catalog table with type specifications.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from loguru import logger

from config.theme import (
    BORDER_DEFAULT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.safe_callback import safe_callback

# Sensor type definitions with display colors
_SENSOR_TYPES: list[dict[str, str]] = [
    {"key": "temperature", "label": "Temp/Humidity", "color": "#0071E3"},
    {"key": "co2", "label": "CO2", "color": "#34C759"},
    {"key": "occupancy", "label": "Occupancy PIR", "color": "#FF9500"},
    {"key": "energy", "label": "Energy Meter", "color": "#FF3B30"},
]

# Coverage radius in meters per sensor type (used for circle shapes)
_COVERAGE_RADIUS: dict[str, float] = {
    "temperature": 3.0,
    "co2": 2.5,
    "occupancy": 4.0,
    "energy": 1.5,
}


def register_sensor_coverage_callbacks(app: object) -> None:
    """Register all Sensor Coverage page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_coverage_graph(app)
    _register_catalog_table(app)


def _generate_sensor_positions(
    zone_id: str,
    center: tuple[float, float],
) -> list[dict[str, Any]]:
    """Generate synthetic sensor positions near a zone centroid.

    Uses a deterministic hash of the zone_id to produce stable positions
    across rerenders. Each zone gets one sensor per type, offset slightly
    from the centroid.

    Args:
        zone_id: Zone identifier for deterministic seeding.
        center: (x, y) centroid of the zone.

    Returns:
        List of dicts with keys: x, y, type, label, color.
    """
    seed = int(hashlib.md5(zone_id.encode()).hexdigest()[:8], 16) % (2**31)
    rng = np.random.default_rng(seed)

    sensors: list[dict[str, Any]] = []
    for stype in _SENSOR_TYPES:
        offset_x = rng.uniform(-1.2, 1.2)
        offset_y = rng.uniform(-1.2, 1.2)
        sensors.append(
            {
                "x": center[0] + offset_x,
                "y": center[1] + offset_y,
                "type": stype["key"],
                "label": stype["label"],
                "color": stype["color"],
            }
        )
    return sensors


def _register_coverage_graph(app: object) -> None:
    """Render sensor coverage floorplan when inputs change."""

    @app.callback(
        Output("sensors-coverage-graph", "figure"),
        Input("building-state-store", "data"),
        Input("sensors-floor-selector", "value"),
        Input("sensors-coverage-mode", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_sensor_coverage(
        state_data: dict | None,
        floor_value: str | None,
        mode: str | None,
        pathname: str | None,
    ) -> go.Figure:
        """Render the sensor coverage floorplan for the selected floor and mode.

        Args:
            state_data: Serialized BuildingState dict from the store.
            floor_value: Selected floor as string ("0" or "1").
            mode: Coverage visualization mode (coverage/deployment/battery).
            pathname: Current URL pathname for lazy-load guard.

        Returns:
            Plotly Figure with sensor overlay, or no_update when not on page.
        """
        if pathname != "/view_sensors":
            return no_update

        from views.floorplan.renderer_2d import render_floorplan_2d
        from views.floorplan.zones_geometry import (
            get_zone_center,
            get_zones_for_floor,
        )

        floor = int(floor_value) if floor_value is not None else 0
        mode = mode or "coverage"

        # Extract zone_data from building state
        zone_data: dict[str, dict[str, Any]] = {}
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
                        "status": zone.get("status", "unknown"),
                    }

        # Render the base floorplan
        fig = render_floorplan_2d(
            floor=floor,
            zone_data=zone_data,
            metric="freedom_index",
        )

        # Collect all sensor positions for this floor
        zones_geom = get_zones_for_floor(floor)
        all_sensors: list[dict[str, Any]] = []
        for zg in zones_geom:
            center = get_zone_center(zg.id)
            if center == (0.0, 0.0):
                continue
            sensors = _generate_sensor_positions(zg.id, center)
            for s in sensors:
                s["zone_id"] = zg.id
            all_sensors.extend(sensors)

        # ── Battery mode: generate synthetic battery levels ──
        if mode == "battery":
            rng_bat = np.random.default_rng(42 + floor)
            for sensor in all_sensors:
                battery_pct = rng_bat.uniform(10, 100)
                sensor["battery"] = battery_pct
                if battery_pct >= 60:
                    sensor["color"] = "#34C759"  # good
                elif battery_pct >= 30:
                    sensor["color"] = "#FF9500"  # medium
                else:
                    sensor["color"] = "#FF3B30"  # low

        # ── Add sensor scatter traces grouped by type/color ──
        if mode == "battery":
            # Group by battery status color
            groups: dict[str, list[dict]] = {}
            for s in all_sensors:
                key = s["color"]
                groups.setdefault(key, []).append(s)

            color_labels = {
                "#34C759": "Battery Good (>60%)",
                "#FF9500": "Battery Medium (30-60%)",
                "#FF3B30": "Battery Low (<30%)",
            }
            for color, group_sensors in groups.items():
                hover_texts = [
                    f"{s['label']}<br>Zone: {s['zone_id']}<br>"
                    f"Battery: {s['battery']:.0f}%"
                    for s in group_sensors
                ]
                fig.add_trace(
                    go.Scatter(
                        x=[s["x"] for s in group_sensors],
                        y=[s["y"] for s in group_sensors],
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=color,
                            symbol="circle",
                            line=dict(width=1.5, color="#FFFFFF"),
                        ),
                        hovertext=hover_texts,
                        hoverinfo="text",
                        name=color_labels.get(color, "Sensor"),
                        showlegend=True,
                    )
                )
        else:
            # Group by sensor type
            type_groups: dict[str, list[dict]] = {}
            for s in all_sensors:
                type_groups.setdefault(s["type"], []).append(s)

            for stype in _SENSOR_TYPES:
                group_sensors = type_groups.get(stype["key"], [])
                if not group_sensors:
                    continue

                hover_texts = [
                    f"{s['label']}<br>Zone: {s['zone_id']}" for s in group_sensors
                ]
                fig.add_trace(
                    go.Scatter(
                        x=[s["x"] for s in group_sensors],
                        y=[s["y"] for s in group_sensors],
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=stype["color"],
                            symbol="circle",
                            line=dict(width=1.5, color="#FFFFFF"),
                        ),
                        hovertext=hover_texts,
                        hoverinfo="text",
                        name=stype["label"],
                        showlegend=True,
                    )
                )

        # ── Coverage mode: add circle shapes around sensors ──
        if mode == "coverage":
            shapes = list(fig.layout.shapes) if fig.layout.shapes else []
            for sensor in all_sensors:
                radius = _COVERAGE_RADIUS.get(sensor["type"], 2.5)
                r, g, b = _hex_to_rgb(sensor["color"])
                shapes.append(
                    dict(
                        type="circle",
                        xref="x",
                        yref="y",
                        x0=sensor["x"] - radius,
                        y0=sensor["y"] - radius,
                        x1=sensor["x"] + radius,
                        y1=sensor["y"] + radius,
                        fillcolor=f"rgba({r}, {g}, {b}, 0.08)",
                        line=dict(
                            color=f"rgba({r}, {g}, {b}, 0.25)",
                            width=1,
                            dash="dot",
                        ),
                        layer="above",
                    )
                )
            fig.update_layout(shapes=shapes)

        # Show legend for sensor types
        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
            ),
            height=520,
        )

        logger.debug(
            f"Sensor coverage rendered: floor={floor}, mode={mode}, "
            f"sensors={len(all_sensors)}"
        )
        return fig


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to an (r, g, b) tuple.

    Args:
        hex_color: Hex color string (e.g. '#0071E3').

    Returns:
        Tuple of (red, green, blue) integer values 0-255.
    """
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _register_catalog_table(app: object) -> None:
    """Populate the sensor catalog table on page load."""

    @app.callback(
        Output("sensors-catalog-table", "children"),
        Input("url", "pathname"),
    )
    @safe_callback
    def update_catalog_table(pathname: str | None) -> html.Table:
        """Render the sensor catalog table with type specifications.

        Args:
            pathname: Current URL pathname for page guard.

        Returns:
            html.Table with sensor type rows, or no_update if not on page.
        """
        if pathname != "/view_sensors":
            return no_update

        # Sensor catalog data
        catalog = [
            {
                "name": "Temp/Humidity",
                "type": "DHT22 / SHT31",
                "cost": "€15 - €25",
                "coverage": "3 m radius",
                "battery": "18 months",
            },
            {
                "name": "CO2",
                "type": "SCD30 / MH-Z19",
                "cost": "€30 - €55",
                "coverage": "2.5 m radius",
                "battery": "12 months",
            },
            {
                "name": "Occupancy PIR",
                "type": "HC-SR501 / AM312",
                "cost": "€5 - €12",
                "coverage": "4 m radius",
                "battery": "24 months",
            },
            {
                "name": "Energy Meter",
                "type": "SCT-013 / PZEM-004T",
                "cost": "€8 - €20",
                "coverage": "1.5 m (panel)",
                "battery": "Mains powered",
            },
            {
                "name": "Smoke/Fire",
                "type": "MQ-2 / Photoelectric",
                "cost": "€10 - €30",
                "coverage": "5 m radius",
                "battery": "36 months",
            },
        ]

        # Table header style
        th_style: dict[str, str] = {
            "padding": "10px 14px",
            "fontSize": "12px",
            "fontWeight": "600",
            "color": TEXT_SECONDARY,
            "textAlign": "left",
            "borderBottom": f"2px solid {BORDER_DEFAULT}",
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
        }

        # Table cell style
        td_style: dict[str, str] = {
            "padding": "10px 14px",
            "fontSize": "13px",
            "color": TEXT_PRIMARY,
            "borderBottom": f"1px solid {BORDER_DEFAULT}",
        }

        td_secondary_style: dict[str, str] = {
            "padding": "10px 14px",
            "fontSize": "13px",
            "color": TEXT_TERTIARY,
            "borderBottom": f"1px solid {BORDER_DEFAULT}",
        }

        columns = ["Name", "Type", "Cost", "Coverage", "Battery"]

        header_row = html.Tr([html.Th(col, style=th_style) for col in columns])

        body_rows = []
        for row in catalog:
            body_rows.append(
                html.Tr(
                    [
                        html.Td(row["name"], style=td_style),
                        html.Td(row["type"], style=td_secondary_style),
                        html.Td(row["cost"], style=td_style),
                        html.Td(row["coverage"], style=td_secondary_style),
                        html.Td(row["battery"], style=td_secondary_style),
                    ]
                )
            )

        return html.Table(
            [
                html.Thead(header_row),
                html.Tbody(body_rows),
            ],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
                "borderSpacing": "0",
            },
        )
