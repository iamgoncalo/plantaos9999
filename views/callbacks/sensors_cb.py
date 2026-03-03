"""Sensors management callbacks — inventory, health, actions."""

from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, html, no_update
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
        "rssi_dbm": -42,
        "notes": "",
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
        "rssi_dbm": -55,
        "notes": "",
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
        "rssi_dbm": -38,
        "notes": "",
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
        "rssi_dbm": -61,
        "notes": "Near window, may need recalibration",
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
        "rssi_dbm": -72,
        "notes": "Battery replacement scheduled",
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
        "rssi_dbm": -45,
        "notes": "",
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
        "rssi_dbm": -40,
        "notes": "Safety-critical device",
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
        "rssi_dbm": -88,
        "notes": "Offline, weak signal",
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
        "rssi_dbm": -68,
        "notes": "Connection intermittent",
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
        "rssi_dbm": None,
        "notes": "Wired connection, check Modbus link",
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
        "rssi_dbm": -50,
        "notes": "",
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
        "rssi_dbm": -44,
        "notes": "",
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


def _rssi_indicator(rssi: int | None) -> html.Span:
    """Render RSSI signal strength with color coding.

    Args:
        rssi: RSSI in dBm or None for wired devices.

    Returns:
        html.Span with RSSI display.
    """
    if rssi is None:
        return html.Span(
            "N/A",
            style={
                "fontSize": "13px",
                "color": TEXT_TERTIARY,
                "fontFamily": "JetBrains Mono",
            },
        )

    if rssi > -50:
        color = STATUS_HEALTHY
    elif rssi > -70:
        color = STATUS_WARNING
    else:
        color = STATUS_CRITICAL

    return html.Span(
        f"{rssi} dBm",
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
    _register_health_notifications(app)
    _register_device_select(app)
    _register_add_device(app)
    _register_commission_device(app)
    _register_remove_device(app)
    _register_fusion_panel(app)


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
            "RSSI",
            "Last Seen",
            "Firmware",
            "Notes",
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
                            _battery_indicator(
                                device.get("battery_pct"),
                            ),
                            style={"padding": "10px 12px"},
                        ),
                        html.Td(
                            _rssi_indicator(
                                device.get("rssi_dbm"),
                            ),
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
                        html.Td(
                            device.get("notes", ""),
                            style={
                                "padding": "10px 12px",
                                "fontSize": "12px",
                                "color": TEXT_TERTIARY,
                                "maxWidth": "160px",
                                "overflow": "hidden",
                                "textOverflow": "ellipsis",
                                "whiteSpace": "nowrap",
                            },
                        ),
                    ],
                    id={
                        "type": "sensor-row",
                        "index": device.get("device_id", ""),
                    },
                    style={
                        "borderBottom": "1px solid #F2F2F7",
                        "cursor": "pointer",
                    },
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


def _register_health_notifications(app: object) -> None:
    """Generate health alert notifications for sensor issues.

    Rules:
    - Offline > 10 min: alert notification
    - Battery < 15%: warning notification
    """

    @app.callback(
        Output("sensors-health-notifications", "children"),
        Input("url", "pathname"),
        Input("sensors-store", "data"),
    )
    @safe_callback
    def render_health_notifications(
        pathname: str | None,
        stored_sensors: list | None,
    ) -> html.Div:
        """Build notification list for devices with health issues.

        Args:
            pathname: Current URL path.
            stored_sensors: Persisted sensor list from store.

        Returns:
            Dash component with alert/warning notifications.
        """
        if pathname != "/sensors":
            return no_update

        devices = (
            stored_sensors
            if stored_sensors and len(stored_sensors) > 0
            else _SIMULATED_DEVICES
        )

        notifications: list[html.Div] = []
        for device in devices:
            battery = device.get("battery_pct")
            last_seen = device.get("last_seen", "")
            minutes = _parse_last_seen_minutes(last_seen)
            dev_label = f"{device['device_id']} - {device['name']}"

            if minutes > 10:
                notifications.append(
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:alert-circle",
                                width=16,
                                color=STATUS_CRITICAL,
                            ),
                            html.Span(
                                f"ALERT: {dev_label} offline for {last_seen}",
                                style={
                                    "fontSize": "13px",
                                    "color": STATUS_CRITICAL,
                                    "fontWeight": 500,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "padding": "8px 12px",
                            "background": "#FFE5E3",
                            "borderRadius": "8px",
                            "marginBottom": "6px",
                        },
                    )
                )

            if battery is not None and battery < 15:
                notifications.append(
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:battery-low",
                                width=16,
                                color=STATUS_WARNING,
                            ),
                            html.Span(
                                f"WARNING: {dev_label} battery at {battery}%",
                                style={
                                    "fontSize": "13px",
                                    "color": STATUS_WARNING,
                                    "fontWeight": 500,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "padding": "8px 12px",
                            "background": "#FFF4E6",
                            "borderRadius": "8px",
                            "marginBottom": "6px",
                        },
                    )
                )

        if not notifications:
            return html.Div(
                "No health notifications",
                style={
                    "color": TEXT_TERTIARY,
                    "fontSize": "13px",
                    "padding": "8px 0",
                },
            )

        return html.Div(notifications)


def _register_device_select(app: object) -> None:
    """Track which device row the user clicked."""

    @app.callback(
        Output("sensors-selected-device", "data"),
        Input({"type": "sensor-row", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def select_device(n_clicks_list: list) -> str:
        """Store the device_id of the clicked row.

        Args:
            n_clicks_list: Click counts for all sensor rows.

        Returns:
            Device ID string of the clicked row.
        """
        if not any(n_clicks_list):
            return no_update
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update
        return triggered_id.get("index", "")


def _register_add_device(app: object) -> None:
    """Add a new sensor device to the inventory."""

    @app.callback(
        Output(
            "sensors-store",
            "data",
            allow_duplicate=True,
        ),
        Input("sensors-add-btn", "n_clicks"),
        State("sensors-store", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def add_device(
        n_clicks: int | None,
        stored: list | None,
    ) -> list:
        """Append a new sensor device to the store.

        Args:
            n_clicks: Add button click count.
            stored: Current device list from store.

        Returns:
            Updated device list with new device appended.
        """
        if not n_clicks:
            return no_update
        devices = list(stored) if stored else list(_SIMULATED_DEVICES)
        new_id = f"SEN-{len(devices) + 1:03d}"
        devices.append(
            {
                "device_id": new_id,
                "name": f"Sensor {new_id}",
                "type": "multi",
                "protocol": "Matter",
                "zone_id": "p0_hall",
                "status": "commissioning",
                "battery_pct": 100,
                "last_seen": "just now",
                "firmware": "1.0.0",
                "metrics": ["temperature_c"],
            }
        )
        return devices


def _register_commission_device(app: object) -> None:
    """Commission a device with confirmation dialog.

    Step 1: Button click opens the sensors-commission-confirm dialog.
    Step 2: Dialog confirmation triggers the actual commission action.
    """

    @app.callback(
        Output("sensors-commission-confirm", "displayed"),
        Input("sensors-commission-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_commission_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before commissioning a device."""
        return bool(n_clicks)

    @app.callback(
        Output(
            "sensors-store",
            "data",
            allow_duplicate=True,
        ),
        Input("sensors-commission-confirm", "submit_n_clicks"),
        State("sensors-store", "data"),
        State("sensors-selected-device", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def commission_device(
        n_clicks: int | None,
        stored: list | None,
        selected_id: str | None,
    ) -> list:
        """Set selected device status to online after confirmation.

        Args:
            n_clicks: Confirm dialog submit click count.
            stored: Current device list from store.
            selected_id: Device ID to commission.

        Returns:
            Updated device list.
        """
        if not n_clicks or not selected_id:
            return no_update
        devices = list(stored) if stored else list(_SIMULATED_DEVICES)
        for device in devices:
            if device.get("device_id") == selected_id:
                device["status"] = "online"
                device["last_seen"] = "just now"
                break
        return devices


def _register_remove_device(app: object) -> None:
    """Remove a device with confirmation dialog.

    Step 1: Button click opens the sensors-remove-confirm dialog.
    Step 2: Dialog confirmation triggers the actual removal.
    """

    @app.callback(
        Output("sensors-remove-confirm", "displayed"),
        Input("sensors-remove-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_remove_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before removing a device."""
        return bool(n_clicks)

    @app.callback(
        Output(
            "sensors-store",
            "data",
            allow_duplicate=True,
        ),
        Input("sensors-remove-confirm", "submit_n_clicks"),
        State("sensors-store", "data"),
        State("sensors-selected-device", "data"),
        prevent_initial_call=True,
    )
    @safe_callback
    def remove_device(
        n_clicks: int | None,
        stored: list | None,
        selected_id: str | None,
    ) -> list:
        """Remove selected device from the store after confirmation.

        Args:
            n_clicks: Confirm dialog submit click count.
            stored: Current device list from store.
            selected_id: Device ID to remove.

        Returns:
            Updated device list without the removed device.
        """
        if not n_clicks or not selected_id:
            return no_update
        devices = list(stored) if stored else list(_SIMULATED_DEVICES)
        devices = [d for d in devices if d.get("device_id") != selected_id]
        return devices


# ── Monitored zone IDs for fusion diagnostics (first 8) ──
_MONITORED_ZONES: list[str] = [
    "f0_sala_multiusos",
    "f0_hall",
    "f0_biblioteca",
    "f0_sala_formacao_1",
    "f0_zona_social",
    "f0_sala_informatica",
    "f1_sala_dojo_seguranca",
    "f1_sala_grande",
]

# Friendly display names for zone IDs
_ZONE_DISPLAY_NAMES: dict[str, str] = {
    "f0_sala_multiusos": "Sala Multiusos",
    "f0_hall": "Hall",
    "f0_biblioteca": "Biblioteca",
    "f0_sala_formacao_1": "Sala Formacao 1",
    "f0_zona_social": "Zona Social",
    "f0_sala_informatica": "Sala Informatica",
    "f1_sala_dojo_seguranca": "Sala Dojo Seguranca",
    "f1_sala_grande": "Sala Grande",
}


def _register_fusion_panel(app: object) -> None:
    """Render Kalman fusion diagnostics per monitored zone."""

    @app.callback(
        Output("sensors-fusion-content", "children"),
        Input("building-state-store", "data"),
    )
    @safe_callback
    def render_fusion_panel(
        building_state: dict | None,
    ) -> html.Div:
        """Build a table-like layout showing Kalman diagnostics per zone.

        Displays state estimate, uncertainty, and sensor reliability
        for up to 8 monitored zones using core.fuse diagnostics.

        Args:
            building_state: Current building state from store.

        Returns:
            Dash component with fusion diagnostics table or awaiting message.
        """
        from core.fuse import get_kalman_diagnostics

        rows: list[html.Tr] = []
        for zone_id in _MONITORED_ZONES[:8]:
            diag = get_kalman_diagnostics(zone_id)
            temp_data = diag.get("temperature_c")

            display_name = _ZONE_DISPLAY_NAMES.get(zone_id, zone_id)

            if temp_data:
                x_hat = temp_data.get("x_hat", 0.0)
                P = temp_data.get("P", 0.0)
                R = temp_data.get("R", 0.0)
                # Reliability: lower P and R = more reliable
                # Score = max(0, 100 - (P + R) * 10), clamped to 0-100
                reliability = max(0.0, min(100.0, 100.0 - (P + R) * 10.0))

                if reliability >= 80.0:
                    rel_color = STATUS_HEALTHY
                elif reliability >= 50.0:
                    rel_color = STATUS_WARNING
                else:
                    rel_color = STATUS_CRITICAL

                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                display_name,
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "14px",
                                    "fontWeight": 500,
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Td(
                                f"{x_hat:.2f} \u00b0C",
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "13px",
                                    "fontFamily": "JetBrains Mono",
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Td(
                                f"\u00b1{P:.4f}",
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "13px",
                                    "fontFamily": "JetBrains Mono",
                                    "color": TEXT_SECONDARY,
                                },
                            ),
                            html.Td(
                                html.Span(
                                    f"{reliability:.0f}%",
                                    style={
                                        "fontSize": "12px",
                                        "fontWeight": 500,
                                        "color": rel_color,
                                        "fontFamily": "JetBrains Mono",
                                    },
                                ),
                                style={"padding": "10px 12px"},
                            ),
                        ],
                        style={"borderBottom": "1px solid #F2F2F7"},
                    )
                )
            else:
                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                display_name,
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "14px",
                                    "fontWeight": 500,
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Td(
                                "\u2014",
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "13px",
                                    "color": TEXT_TERTIARY,
                                },
                            ),
                            html.Td(
                                "\u2014",
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "13px",
                                    "color": TEXT_TERTIARY,
                                },
                            ),
                            html.Td(
                                "\u2014",
                                style={
                                    "padding": "10px 12px",
                                    "fontSize": "13px",
                                    "color": TEXT_TERTIARY,
                                },
                            ),
                        ],
                        style={"borderBottom": "1px solid #F2F2F7"},
                    )
                )

        if not rows:
            return html.Div(
                "Fusion pipeline active \u2014 awaiting sensor data",
                style={
                    "color": TEXT_SECONDARY,
                    "fontSize": "13px",
                    "padding": "16px 0",
                },
            )

        header_cols = [
            "Zone",
            "Kalman Estimate (x\u0302)",
            "Uncertainty (P)",
            "Reliability",
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

        return html.Table(
            [header, html.Tbody(rows)],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
            },
        )
