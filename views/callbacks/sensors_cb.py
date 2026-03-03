"""Sensors management callbacks — inventory, health, actions."""

from __future__ import annotations

from dash import Input, Output, html, no_update
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback

# ── Simulated device inventory ──────────────────────
_SIMULATED_DEVICES: list[dict] = [
    {
        "device_id": "SEN-001",
        "name": "Temp/Humidity Combo",
        "type": "temp_humidity",
        "protocol": "Matter",
        "zone_id": "f0_sala_multiusos",
        "status": "online",
        "battery_pct": 85,
        "last_seen": "2 min ago",
        "firmware": "2.1.0",
        "metrics": ["temperature_c", "humidity_pct"],
    },
    {
        "device_id": "SEN-002",
        "name": "CO2 Sensor",
        "type": "co2",
        "protocol": "Matter",
        "zone_id": "f0_sala_multiusos",
        "status": "online",
        "battery_pct": 72,
        "last_seen": "1 min ago",
        "firmware": "1.8.3",
        "metrics": ["co2_ppm"],
    },
    {
        "device_id": "SEN-003",
        "name": "PIR Occupancy Sensor",
        "type": "occupancy",
        "protocol": "BLE",
        "zone_id": "f0_hall",
        "status": "online",
        "battery_pct": 91,
        "last_seen": "30 sec ago",
        "firmware": "1.2.0",
        "metrics": ["occupancy_count"],
    },
    {
        "device_id": "SEN-004",
        "name": "Lux Meter",
        "type": "illuminance",
        "protocol": "MQTT",
        "zone_id": "f0_biblioteca",
        "status": "online",
        "battery_pct": 64,
        "last_seen": "3 min ago",
        "firmware": "1.5.1",
        "metrics": ["illuminance_lux"],
    },
    {
        "device_id": "SEN-005",
        "name": "Temp Probe A",
        "type": "temperature",
        "protocol": "Matter",
        "zone_id": "f0_sala_formacao_1",
        "status": "warning",
        "battery_pct": 12,
        "last_seen": "5 min ago",
        "firmware": "2.0.4",
        "metrics": ["temperature_c"],
    },
    {
        "device_id": "SEN-006",
        "name": "Multi-Sensor Hub",
        "type": "multi",
        "protocol": "Matter",
        "zone_id": "f0_zona_social",
        "status": "online",
        "battery_pct": 78,
        "last_seen": "1 min ago",
        "firmware": "3.1.0",
        "metrics": ["temperature_c", "humidity_pct", "co2_ppm"],
    },
    {
        "device_id": "SEN-007",
        "name": "Smoke/CO Detector",
        "type": "safety",
        "protocol": "Matter",
        "zone_id": "f0_sala_informatica",
        "status": "online",
        "battery_pct": 95,
        "last_seen": "1 min ago",
        "firmware": "1.0.2",
        "metrics": ["smoke_detected", "co_ppm"],
    },
    {
        "device_id": "SEN-008",
        "name": "Humidity Sensor B",
        "type": "humidity",
        "protocol": "MQTT",
        "zone_id": "f1_sala_dojo_seguranca",
        "status": "critical",
        "battery_pct": 5,
        "last_seen": "45 min ago",
        "firmware": "1.3.0",
        "metrics": ["humidity_pct"],
    },
    {
        "device_id": "SEN-009",
        "name": "Door Contact Sensor",
        "type": "contact",
        "protocol": "BLE",
        "zone_id": "f1_sala_grande",
        "status": "warning",
        "battery_pct": 18,
        "last_seen": "12 min ago",
        "firmware": "1.1.1",
        "metrics": ["door_open"],
    },
    {
        "device_id": "SEN-010",
        "name": "Energy Meter",
        "type": "energy",
        "protocol": "Modbus",
        "zone_id": "f0_sala_informatica",
        "status": "warning",
        "battery_pct": None,
        "last_seen": "15 min ago",
        "firmware": "3.0.1",
        "metrics": ["total_kwh"],
    },
    {
        "device_id": "SEN-011",
        "name": "CO2 + Temp Combo",
        "type": "co2_temp",
        "protocol": "Matter",
        "zone_id": "f1_arquivo",
        "status": "online",
        "battery_pct": 67,
        "last_seen": "2 min ago",
        "firmware": "2.2.1",
        "metrics": ["co2_ppm", "temperature_c"],
    },
    {
        "device_id": "SEN-012",
        "name": "Occupancy Counter",
        "type": "occupancy",
        "protocol": "MQTT",
        "zone_id": "f0_recepcao",
        "status": "online",
        "battery_pct": 88,
        "last_seen": "1 min ago",
        "firmware": "2.0.0",
        "metrics": ["occupancy_count"],
    },
]


def _parse_last_seen_minutes(last_seen: str) -> float:
    """Parse a 'last_seen' string into approximate minutes.

    Args:
        last_seen: Human-readable time string (e.g., '2 min ago').

    Returns:
        Approximate minutes since last seen.
    """
    try:
        parts = last_seen.lower().replace("ago", "").strip().split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1]
            if "sec" in unit:
                return val / 60.0
            if "min" in unit:
                return val
            if "hour" in unit or "hr" in unit:
                return val * 60.0
        return 0.0
    except (ValueError, IndexError):
        return 0.0


def _device_effective_status(device: dict) -> str:
    """Compute effective status based on battery and last_seen.

    Health rules:
    - battery < 15% -> warning
    - last_seen > 10 min -> warning
    - last_seen > 30 min -> critical
    - battery < 5% -> critical

    Args:
        device: Device dict with battery_pct and last_seen fields.

    Returns:
        Effective status string: 'online', 'warning', or 'critical'.
    """
    battery = device.get("battery_pct")
    last_seen = device.get("last_seen", "")
    minutes = _parse_last_seen_minutes(last_seen)

    # Critical checks first
    if minutes > 30:
        return "critical"
    if battery is not None and battery < 5:
        return "critical"

    # Warning checks
    if minutes > 10:
        return "warning"
    if battery is not None and battery < 15:
        return "warning"

    return device.get("status", "online")


def _status_badge(status: str) -> html.Span:
    """Create a colored status badge.

    Args:
        status: Device status string.

    Returns:
        html.Span with appropriate styling.
    """
    color_map = {
        "online": STATUS_HEALTHY,
        "warning": STATUS_WARNING,
        "critical": STATUS_CRITICAL,
    }
    bg_map = {
        "online": "#E8F9EE",
        "warning": "#FFF4E6",
        "critical": "#FFE5E3",
    }
    color = color_map.get(status, TEXT_TERTIARY)
    bg = bg_map.get(status, "#F2F2F7")

    return html.Span(
        status.capitalize(),
        style={
            "fontSize": "12px",
            "fontWeight": 500,
            "color": color,
            "padding": "2px 10px",
            "borderRadius": "8px",
            "background": bg,
        },
    )


def _battery_indicator(pct: int | None) -> html.Span:
    """Render battery percentage with color coding.

    Args:
        pct: Battery percentage or None for mains-powered.

    Returns:
        html.Span with battery display.
    """
    if pct is None:
        return html.Span(
            "Mains",
            style={
                "fontSize": "13px",
                "color": TEXT_TERTIARY,
                "fontFamily": "JetBrains Mono",
            },
        )

    if pct < 15:
        color = STATUS_CRITICAL
    elif pct < 30:
        color = STATUS_WARNING
    else:
        color = STATUS_HEALTHY

    return html.Span(
        f"{pct}%",
        style={
            "fontSize": "13px",
            "color": color,
            "fontWeight": 500,
            "fontFamily": "JetBrains Mono",
        },
    )


def register_sensors_callbacks(app: object) -> None:
    """Register all sensor management page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_inventory(app)
    _register_kpi_strip(app)
    _register_health_panel(app)


def _register_inventory(app: object) -> None:
    """Render device inventory table."""

    @app.callback(
        Output("sensors-inventory-table", "children"),
        Input("url", "pathname"),
        Input("sensors-store", "data"),
    )
    @safe_callback
    def render_inventory(
        pathname: str | None,
        stored_sensors: list | None,
    ) -> html.Table | html.Div:
        """Build HTML table with device rows.

        Args:
            pathname: Current URL path.
            stored_sensors: Persisted sensor list from store.

        Returns:
            Inventory table or no_update.
        """
        if pathname != "/sensors":
            return no_update

        devices = (
            stored_sensors
            if stored_sensors and len(stored_sensors) > 0
            else _SIMULATED_DEVICES
        )

        # Table header
        header_cols = [
            "ID",
            "Name",
            "Type",
            "Protocol",
            "Zone",
            "Status",
            "Battery",
            "Last Seen",
            "Firmware",
        ]
        header = html.Thead(
            html.Tr(
                [
                    html.Th(
                        col,
                        style={
                            "textAlign": "left",
                            "padding": "8px 12px",
                            "fontSize": "12px",
                            "fontWeight": 600,
                            "color": TEXT_TERTIARY,
                            "borderBottom": "1px solid #E5E5EA",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.5px",
                        },
                    )
                    for col in header_cols
                ]
            )
        )

        # Table body rows
        rows = []
        for device in devices:
            eff_status = _device_effective_status(device)
            rows.append(
                html.Tr(
                    [
                        html.Td(
                            device.get("device_id", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "fontWeight": 500,
                                "color": TEXT_PRIMARY,
                                "fontFamily": "JetBrains Mono",
                            },
                        ),
                        html.Td(
                            device.get("name", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "14px",
                                "fontWeight": 500,
                                "color": TEXT_PRIMARY,
                            },
                        ),
                        html.Td(
                            device.get("type", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "color": TEXT_SECONDARY,
                            },
                        ),
                        html.Td(
                            html.Span(
                                device.get("protocol", ""),
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": 500,
                                    "color": (
                                        ACCENT_BLUE
                                        if device.get("protocol") == "Matter"
                                        else TEXT_SECONDARY
                                    ),
                                    "padding": "2px 8px",
                                    "borderRadius": "6px",
                                    "background": (
                                        "#E8F5EE"
                                        if device.get("protocol") == "Matter"
                                        else "#F2F2F7"
                                    ),
                                },
                            ),
                            style={"padding": "10px 12px"},
                        ),
                        html.Td(
                            device.get("zone_id", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "color": TEXT_SECONDARY,
                            },
                        ),
                        html.Td(
                            _status_badge(eff_status),
                            style={"padding": "10px 12px"},
                        ),
                        html.Td(
                            _battery_indicator(device.get("battery_pct")),
                            style={"padding": "10px 12px"},
                        ),
                        html.Td(
                            device.get("last_seen", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "color": TEXT_SECONDARY,
                            },
                        ),
                        html.Td(
                            device.get("firmware", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "color": TEXT_TERTIARY,
                                "fontFamily": "JetBrains Mono",
                            },
                        ),
                    ],
                    style={"borderBottom": "1px solid #F2F2F7"},
                )
            )

        body = html.Tbody(rows)

        return html.Table(
            [header, body],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
            },
        )


def _register_kpi_strip(app: object) -> None:
    """Update KPI cards: total, online, warning, critical."""

    @app.callback(
        Output("sensors-kpi-strip", "children"),
        Input("url", "pathname"),
        Input("sensors-store", "data"),
    )
    @safe_callback
    def update_kpi_strip(
        pathname: str | None,
        stored_sensors: list | None,
    ) -> list:
        """Compute sensor KPI counts and render cards.

        Args:
            pathname: Current URL path.
            stored_sensors: Persisted sensor list from store.

        Returns:
            List of KPI card components.
        """
        if pathname != "/sensors":
            return no_update

        devices = (
            stored_sensors
            if stored_sensors and len(stored_sensors) > 0
            else _SIMULATED_DEVICES
        )

        total = len(devices)
        online = 0
        warnings = 0
        critical = 0

        for device in devices:
            eff = _device_effective_status(device)
            if eff == "online":
                online += 1
            elif eff == "warning":
                warnings += 1
            elif eff == "critical":
                critical += 1

        return [
            create_kpi_card(
                "Total Sensors",
                str(total),
                icon="mdi:access-point",
            ),
            create_kpi_card(
                "Online",
                str(online),
                icon="mdi:check-circle-outline",
            ),
            create_kpi_card(
                "Warnings",
                str(warnings),
                icon="mdi:alert-outline",
            ),
            create_kpi_card(
                "Critical",
                str(critical),
                icon="mdi:alert-circle",
            ),
        ]


def _register_health_panel(app: object) -> None:
    """Show devices needing attention (low battery, stale connection)."""

    @app.callback(
        Output("sensors-health-panel", "children"),
        Input("url", "pathname"),
        Input("sensors-store", "data"),
    )
    @safe_callback
    def render_health_panel(
        pathname: str | None,
        stored_sensors: list | None,
    ) -> html.Div:
        """Render health alerts for devices with issues.

        Args:
            pathname: Current URL path.
            stored_sensors: Persisted sensor list from store.

        Returns:
            Dash component with health alerts or all-clear message.
        """
        if pathname != "/sensors":
            return no_update

        devices = (
            stored_sensors
            if stored_sensors and len(stored_sensors) > 0
            else _SIMULATED_DEVICES
        )

        issues: list[html.Div] = []

        for device in devices:
            device_issues: list[str] = []
            battery = device.get("battery_pct")
            last_seen = device.get("last_seen", "")
            minutes = _parse_last_seen_minutes(last_seen)

            if battery is not None and battery < 15:
                device_issues.append(f"Battery low ({battery}%)")
            if minutes > 30:
                device_issues.append(f"Offline ({last_seen})")
            elif minutes > 10:
                device_issues.append(f"Connection stale ({last_seen})")

            if device_issues:
                eff = _device_effective_status(device)
                icon_color = STATUS_CRITICAL if eff == "critical" else STATUS_WARNING
                icon_name = (
                    "mdi:alert-circle" if eff == "critical" else "mdi:alert-outline"
                )

                issues.append(
                    html.Div(
                        [
                            DashIconify(
                                icon=icon_name,
                                width=18,
                                color=icon_color,
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        f"{device['device_id']} — {device['name']}",
                                        style={
                                            "fontWeight": 500,
                                            "fontSize": "14px",
                                            "color": TEXT_PRIMARY,
                                        },
                                    ),
                                    html.Span(
                                        " · ".join(device_issues),
                                        style={
                                            "fontSize": "13px",
                                            "color": TEXT_SECONDARY,
                                            "marginLeft": "8px",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "2px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "flex-start",
                            "gap": "12px",
                            "padding": "10px 0",
                            "borderBottom": "1px solid #F2F2F7",
                        },
                    )
                )

        if not issues:
            return html.Div(
                [
                    DashIconify(
                        icon="mdi:check-circle-outline",
                        width=32,
                        color=STATUS_HEALTHY,
                    ),
                    html.Div(
                        "All sensors operating normally",
                        style={
                            "color": TEXT_SECONDARY,
                            "fontSize": "14px",
                            "marginTop": "8px",
                        },
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "32px 16px",
                },
            )

        return html.Div(issues)
