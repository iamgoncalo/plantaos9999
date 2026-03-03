"""Zone detail overlay panel.

Renders a slide-in panel showing detailed metrics, charts, and
status for a selected building zone. Appears on the right side.
Also provides an inline zone detail component for the overview page.
"""

from __future__ import annotations

from typing import Any

from dash import html
from dash_iconify import DashIconify

from config.building import get_zone_by_id
from config.theme import (
    FONT_SIZE_XS,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WEIGHT_SEMIBOLD,
)
from utils.colors import zone_health_to_color


def create_zone_panel(zone_id: str | None = None) -> html.Div:
    """Create the zone detail overlay panel.

    Args:
        zone_id: Zone to display details for. None hides the panel.

    Returns:
        Dash html.Div with zone detail layout.
    """
    if zone_id is None:
        return html.Div(
            id="zone-panel",
            className="zone-panel zone-panel-hidden",
        )

    zone = get_zone_by_id(zone_id)
    if zone is None:
        return html.Div(
            id="zone-panel",
            className="zone-panel zone-panel-hidden",
        )

    close_btn = html.Button(
        DashIconify(icon="mdi:close", width=18),
        className="zone-panel-close",
        id="zone-panel-close",
    )

    header = html.Div(
        [
            html.H2(
                zone.name,
                style={"fontSize": "17px", "fontWeight": 600, "margin": 0},
            ),
            html.Div(
                [
                    html.Span(
                        zone.zone_type.value.replace("_", " ").title(),
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    html.Span(" · "),
                    html.Span(
                        f"{zone.area_m2:.0f} m²",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_TERTIARY,
                        },
                    ),
                    html.Span(" · ") if zone.capacity else None,
                    html.Span(
                        f"Cap. {zone.capacity}",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_TERTIARY,
                        },
                    )
                    if zone.capacity
                    else None,
                ],
                style={"marginTop": "4px"},
            ),
        ],
        className="zone-panel-header",
    )

    metrics_placeholder = html.Div(
        id="zone-panel-metrics",
        children=[
            html.Div(
                "Select a zone to view detailed metrics",
                className="empty-state",
            ),
        ],
        style={"marginTop": "24px"},
    )

    return html.Div(
        id="zone-panel",
        className="zone-panel",
        children=[close_btn, header, metrics_placeholder],
    )


# ── Metric display config ────────────────────
_METRICS: list[dict[str, str]] = [
    {
        "key": "temperature_c",
        "label": "Temperature",
        "icon": "mdi:thermometer",
        "unit": "°C",
        "fmt": ".1f",
    },
    {
        "key": "humidity_pct",
        "label": "Humidity",
        "icon": "mdi:water-percent",
        "unit": "%",
        "fmt": ".0f",
    },
    {
        "key": "co2_ppm",
        "label": "CO₂",
        "icon": "mdi:molecule-co2",
        "unit": "ppm",
        "fmt": ".0f",
    },
    {
        "key": "illuminance_lux",
        "label": "Illuminance",
        "icon": "mdi:lightbulb-outline",
        "unit": "lux",
        "fmt": ".0f",
    },
    {
        "key": "occupant_count",
        "label": "Occupancy",
        "icon": "mdi:account-group",
        "unit": "",
        "fmt": ".0f",
    },
    {
        "key": "total_energy_kwh",
        "label": "Energy",
        "icon": "mdi:flash",
        "unit": "kWh",
        "fmt": ".2f",
    },
]


def create_zone_detail(
    zone_id: str,
    zone_state: dict[str, Any] | None = None,
) -> html.Div:
    """Create an inline zone detail panel for the overview page.

    Args:
        zone_id: Zone identifier.
        zone_state: Zone state dict with metric values.

    Returns:
        Dash html.Div with zone detail layout.
    """
    zone = get_zone_by_id(zone_id)
    if zone is None:
        return html.Div("Zone not found", className="empty-state")

    zone_state = zone_state or {}

    # Header
    header = html.Div(
        [
            html.H3(
                zone.name,
                style={"fontSize": "15px", "fontWeight": WEIGHT_SEMIBOLD, "margin": 0},
            ),
            html.Div(
                [
                    html.Span(
                        zone.zone_type.value.replace("_", " ").title(),
                        className="status-badge healthy"
                        if zone_state.get("status") in ("optimal", "acceptable")
                        else "status-badge warning"
                        if zone_state.get("status") == "warning"
                        else "status-badge critical"
                        if zone_state.get("status") == "critical"
                        else "status-badge healthy",
                        style={"fontSize": FONT_SIZE_XS},
                    ),
                    html.Span(
                        f"{zone.area_m2:.0f} m²",
                        style={"fontSize": "12px", "color": TEXT_TERTIARY},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginTop": "4px",
                },
            ),
        ],
        style={"marginBottom": "16px"},
    )

    # Building Health score
    freedom = zone_state.get("freedom_index", 0)
    freedom_color = zone_health_to_color(freedom)
    from utils.colors import hex_to_rgb

    r, g, b = hex_to_rgb(freedom_color)
    freedom_bg = f"rgba({r}, {g}, {b}, 0.1)"

    freedom_section = html.Div(
        [
            html.Span(
                f"{freedom:.0f}",
                className="zone-freedom-number",
                style={"color": freedom_color},
            ),
            html.Div(
                [
                    html.Div("Zone Performance", className="zone-freedom-label"),
                    html.Div(
                        html.Div(
                            className="freedom-bar-fill",
                            style={
                                "width": f"{max(0, min(100, freedom)):.0f}%",
                                "background": freedom_color,
                            },
                        ),
                        className="freedom-bar",
                    ),
                ],
                style={"flex": 1},
            ),
        ],
        className="zone-freedom-score",
        style={"background": freedom_bg},
    )

    # Metrics grid
    metric_rows = []
    for m in _METRICS:
        val = zone_state.get(m["key"])
        if val is not None:
            formatted = f"{val:{m['fmt']}} {m['unit']}".strip()
        else:
            formatted = "—"

        row = html.Div(
            [
                html.Div(
                    [
                        DashIconify(
                            icon=m["icon"],
                            width=16,
                            color=TEXT_SECONDARY,
                        ),
                        html.Span(m["label"]),
                    ],
                    className="zone-metric-label",
                ),
                html.Span(formatted, className="zone-metric-value"),
            ],
            className="zone-metric-row",
        )
        metric_rows.append(row)

    return html.Div(
        [header, freedom_section, *metric_rows],
        className="zone-detail",
    )
