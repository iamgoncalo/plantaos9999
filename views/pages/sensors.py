"""Sensors management page — device inventory, health, and Matter commissioning."""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    GAP_ELEMENT,
    PADDING_CARD,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from views.components.kpi_card import create_kpi_card


def create_sensors_page() -> html.Div:
    """Create the Sensors management page layout.

    Returns:
        Dash html.Div containing the sensor inventory, health panel,
        KPI strip, and confirmation dialogs.
    """
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:access-point",
                        width=28,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "Sensor Management",
                        style={
                            "margin": 0,
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                },
            ),
            html.P(
                "Deploy, monitor, and manage building sensors. Matter-first approach.",
                style={
                    "margin": "8px 0 0",
                    "color": TEXT_SECONDARY,
                    "fontSize": "14px",
                },
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # KPI strip: Total Sensors, Online, Warnings, Critical
    kpi_strip = html.Div(
        id="sensors-kpi-strip",
        children=[
            create_kpi_card("Total Sensors", "--", icon="mdi:access-point"),
            create_kpi_card("Online", "--", icon="mdi:check-circle-outline"),
            create_kpi_card("Warnings", "--", icon="mdi:alert-outline"),
            create_kpi_card("Critical", "--", icon="mdi:alert-circle"),
        ],
        className="grid-4",
    )

    # Device inventory table
    inventory_section = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        "Device Inventory",
                        style={
                            "fontSize": "15px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                    html.Div(
                        [
                            html.Button(
                                [
                                    DashIconify(
                                        icon="mdi:plus",
                                        width=16,
                                        color="#FFFFFF",
                                    ),
                                    " Add Device",
                                ],
                                id="sensors-add-btn",
                                n_clicks=0,
                                className="sim-trigger-btn",
                                style={
                                    "padding": "8px 16px",
                                    "background": ACCENT_BLUE,
                                    "color": "#FFFFFF",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "4px",
                                },
                            ),
                            html.Button(
                                [
                                    DashIconify(
                                        icon="mdi:check-circle-outline",
                                        width=16,
                                        color="#FFFFFF",
                                    ),
                                    " Commission",
                                ],
                                id="sensors-commission-btn",
                                n_clicks=0,
                                style={
                                    "padding": "8px 16px",
                                    "background": STATUS_HEALTHY,
                                    "color": "#FFFFFF",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "4px",
                                },
                            ),
                            html.Button(
                                [
                                    DashIconify(
                                        icon="mdi:delete-outline",
                                        width=16,
                                        color="#FFFFFF",
                                    ),
                                    " Remove",
                                ],
                                id="sensors-remove-btn",
                                n_clicks=0,
                                style={
                                    "padding": "8px 16px",
                                    "background": STATUS_CRITICAL,
                                    "color": "#FFFFFF",
                                    "border": "none",
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "4px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "8px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "16px",
                },
            ),
            html.Div(id="sensors-inventory-table"),
        ],
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    # Health notifications panel
    notifications_section = html.Div(
        [
            html.Div(
                "Health Notifications",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "marginBottom": "12px",
                },
            ),
            html.Div(id="sensors-health-notifications"),
        ],
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    # Sensor health panel
    health_section = html.Div(
        [
            html.Div(
                "Sensor Health",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "color": TEXT_PRIMARY,
                    "marginBottom": "16px",
                },
            ),
            html.Div(id="sensors-health-panel"),
        ],
        className="card",
        style={
            "padding": f"{PADDING_CARD}px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )

    # Confirmation dialogs
    confirm_remove = dcc.ConfirmDialog(
        id="sensors-remove-confirm",
        message=(
            "Remove this sensor? This action cannot be undone and will be logged."
        ),
    )
    confirm_commission = dcc.ConfirmDialog(
        id="sensors-commission-confirm",
        message=(
            "Commission this device via Matter protocol? "
            "The sensor will start reporting data."
        ),
    )

    # Stores
    sensor_action_store = dcc.Store(id="sensors-action-store", storage_type="memory")
    selected_device_store = dcc.Store(
        id="sensors-selected-device", storage_type="memory"
    )

    return html.Div(
        [
            confirm_remove,
            confirm_commission,
            sensor_action_store,
            selected_device_store,
            page_header,
            kpi_strip,
            html.Div(
                [
                    notifications_section,
                    inventory_section,
                    health_section,
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": f"{GAP_ELEMENT}px",
                },
            ),
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
        },
    )
