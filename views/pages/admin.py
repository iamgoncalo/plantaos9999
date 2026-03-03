"""Admin settings page: pricing, API keys, tenant management, and data controls.

Provides a configuration interface for building operators to manage energy
pricing, integration keys, tenant visibility, and synthetic data regeneration.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    FONT_STACK,
    GAP_ELEMENT,
    PADDING_CARD,
    STATUS_HEALTHY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)


def _label(text: str) -> html.Label:
    """Create a styled form label.

    Args:
        text: Label display text.

    Returns:
        html.Label with consistent styling.
    """
    return html.Label(
        text,
        style={
            "fontSize": "13px",
            "fontWeight": 500,
            "color": TEXT_SECONDARY,
            "marginBottom": "4px",
            "display": "block",
        },
    )


def _input_group(label_text: str, input_component: dcc.Input) -> html.Div:
    """Create a labeled input group with consistent spacing.

    Args:
        label_text: Display text for the label.
        input_component: The Dash input component.

    Returns:
        html.Div wrapping the label and input.
    """
    return html.Div(
        [_label(label_text), input_component],
        style={"marginBottom": "16px"},
    )


def _principle_row(title: str, description: str) -> html.Div:
    """Create a row for the operating principles card.

    Args:
        title: Principle name displayed in bold.
        description: Explanation text for the principle.

    Returns:
        html.Div with title/description flex row.
    """
    return html.Div(
        [
            html.Span(
                title,
                style={
                    "fontWeight": 600,
                    "fontSize": "14px",
                    "color": TEXT_PRIMARY,
                    "minWidth": "160px",
                },
            ),
            html.Span(
                description,
                style={
                    "fontSize": "13px",
                    "color": TEXT_SECONDARY,
                },
            ),
        ],
        style={
            "display": "flex",
            "gap": "16px",
            "padding": "10px 0",
            "borderBottom": "1px solid #F2F2F7",
            "alignItems": "flex-start",
        },
    )


def _build_api_status_badge() -> html.Span:
    """Build a read-only API connection status badge.

    Checks whether the Anthropic API key is configured (not the actual value).

    Returns:
        html.Span with green 'Connected' or gray 'Not configured' badge.
    """
    from config.settings import settings

    api_configured = bool(settings.ANTHROPIC_API_KEY)
    if api_configured:
        return html.Span(
            "Connected",
            style={
                "fontSize": "12px",
                "fontWeight": 500,
                "color": STATUS_HEALTHY,
                "padding": "4px 12px",
                "borderRadius": "8px",
                "background": "#E8F9EE",
            },
        )
    return html.Span(
        "Not configured",
        style={
            "fontSize": "12px",
            "fontWeight": 500,
            "color": TEXT_TERTIARY,
            "padding": "4px 12px",
            "borderRadius": "8px",
            "background": "#F2F2F7",
        },
    )


def _tenant_table() -> html.Table:
    """Build the tenant management HTML table.

    Returns:
        html.Table with three demo tenant rows.
    """
    tenants = [
        ("HORSE Renault", "CFT Aveiro", "800 m\u00b2", "Active"),
        ("Airbus Assembly", "FAL A320", "15,000 m\u00b2", "Demo"),
        ("IKEA Logistics", "DC Almeirim", "42,000 m\u00b2", "Demo"),
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
                for col in ["Name", "Building", "Area", "Status"]
            ]
        )
    )

    rows = []
    for name, building, area, status in tenants:
        status_color = ACCENT_BLUE if status == "Active" else TEXT_TERTIARY
        rows.append(
            html.Tr(
                [
                    html.Td(
                        name,
                        style={
                            "padding": "10px 12px",
                            "fontSize": "14px",
                            "fontWeight": 500,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                    html.Td(
                        building,
                        style={
                            "padding": "10px 12px",
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    html.Td(
                        area,
                        style={
                            "padding": "10px 12px",
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                            "fontFamily": "JetBrains Mono",
                        },
                    ),
                    html.Td(
                        html.Span(
                            status,
                            style={
                                "fontSize": "12px",
                                "fontWeight": 500,
                                "color": status_color,
                                "padding": "2px 10px",
                                "borderRadius": "8px",
                                "background": (
                                    "#E1F0FF" if status == "Active" else "#F2F2F7"
                                ),
                            },
                        ),
                        style={"padding": "10px 12px"},
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
            "marginTop": "8px",
        },
    )


def create_admin_page() -> html.Div:
    """Create the admin settings page layout.

    Returns:
        Dash html.Div containing pricing/integration settings,
        tenant management table, and data regeneration controls.
    """
    return html.Div(
        [
            # -- Session store + confirm dialogs --------------------
            dcc.Store(id="admin-settings-store", storage_type="local"),
            dcc.ConfirmDialog(
                id="admin-confirm-save",
                message="Save these settings?",
            ),
            dcc.ConfirmDialog(
                id="admin-confirm-regen",
                message=(
                    "Regenerate all synthetic data? This will take about 10 seconds."
                ),
            ),
            # -- Header -------------------------------------------
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:cog-outline",
                                width=28,
                                color=ACCENT_BLUE,
                            ),
                            html.H2(
                                "Settings",
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
                            "gap": "10px",
                        },
                    ),
                    html.P(
                        "Configure building parameters, API keys, "
                        "and tenant management.",
                        style={
                            "margin": "6px 0 0",
                            "color": TEXT_SECONDARY,
                            "fontSize": "14px",
                            "maxWidth": "640px",
                        },
                    ),
                ],
                style={"marginBottom": f"{GAP_ELEMENT}px"},
            ),
            # -- Authentication Section ---------------------------
            html.Div(
                [
                    html.H3(
                        "Authentication",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "16px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        id="admin-auth-status",
                        children=html.Span(
                            "Not logged in",
                            style={
                                "fontSize": "13px",
                                "color": TEXT_TERTIARY,
                            },
                        ),
                    ),
                    # Login form
                    html.Div(
                        [
                            _input_group(
                                "Username",
                                dcc.Input(
                                    id="admin-login-username",
                                    type="text",
                                    placeholder="admin",
                                    className="admin-input",
                                ),
                            ),
                            _input_group(
                                "Password",
                                dcc.Input(
                                    id="admin-login-password",
                                    type="password",
                                    placeholder="Password",
                                    className="admin-input",
                                ),
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Login",
                                        id="admin-login-btn",
                                        className="btn-primary",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "Logout",
                                        id="admin-logout-btn",
                                        n_clicks=0,
                                        style={
                                            "padding": "8px 20px",
                                            "background": "#FFFFFF",
                                            "color": TEXT_SECONDARY,
                                            "border": ("1px solid #E5E5EA"),
                                            "borderRadius": "8px",
                                            "fontSize": "13px",
                                            "fontWeight": 500,
                                            "cursor": "pointer",
                                            "fontFamily": FONT_STACK,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "8px",
                                    "marginBottom": "12px",
                                },
                            ),
                            html.Div(
                                id="admin-login-feedback",
                                style={"marginTop": "8px"},
                            ),
                        ],
                        id="admin-login-form",
                    ),
                    # Password reset section
                    html.Div(
                        [
                            html.Div(
                                "Password Reset",
                                style={
                                    "fontWeight": 600,
                                    "fontSize": "14px",
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": "8px",
                                    "marginTop": "16px",
                                    "borderTop": ("1px solid #E5E5EA"),
                                    "paddingTop": "16px",
                                },
                            ),
                            _input_group(
                                "Username to reset",
                                dcc.Input(
                                    id="admin-reset-username",
                                    type="text",
                                    placeholder="Username",
                                    className="admin-input",
                                ),
                            ),
                            _input_group(
                                "New Password",
                                dcc.Input(
                                    id="admin-reset-new-password",
                                    type="password",
                                    placeholder="New password",
                                    className="admin-input",
                                ),
                            ),
                            html.Button(
                                "Reset Password",
                                id="admin-reset-password-btn",
                                n_clicks=0,
                                style={
                                    "padding": "8px 20px",
                                    "background": "#FFFFFF",
                                    "color": STATUS_HEALTHY,
                                    "border": (f"1px solid {STATUS_HEALTHY}"),
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "fontFamily": FONT_STACK,
                                },
                            ),
                            html.Div(
                                id="admin-reset-feedback",
                                style={"marginTop": "8px"},
                            ),
                        ],
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginBottom": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Two-column card layout ---------------------------
            html.Div(
                [
                    # Left card: Pricing & Integration
                    html.Div(
                        [
                            html.H3(
                                "Pricing & Integration",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": "20px",
                                    "marginTop": 0,
                                },
                            ),
                            _input_group(
                                "Energy Cost (\u20ac/kWh)",
                                dcc.Input(
                                    id="admin-energy-price",
                                    type="number",
                                    value=0.15,
                                    step=0.01,
                                    min=0.01,
                                    max=1.0,
                                    className="admin-input",
                                ),
                            ),
                            _input_group(
                                "Average Hourly Wage (\u20ac/hr)",
                                dcc.Input(
                                    id="admin-wage",
                                    type="number",
                                    value=12.0,
                                    step=0.5,
                                    min=5.0,
                                    max=50.0,
                                    className="admin-input",
                                ),
                            ),
                            _input_group(
                                "Anthropic API Key",
                                dcc.Input(
                                    id="admin-api-key",
                                    type="password",
                                    placeholder="sk-...",
                                    className="admin-input",
                                ),
                            ),
                            html.Button(
                                "Save Settings",
                                id="admin-save-btn",
                                className="btn-primary",
                            ),
                            html.Div(
                                id="admin-save-status",
                                style={"marginTop": "12px"},
                            ),
                        ],
                        className="card",
                        style={
                            "padding": f"{PADDING_CARD}px",
                            "background": BG_CARD,
                            "borderRadius": CARD_RADIUS,
                            "boxShadow": CARD_SHADOW,
                            "flex": 1,
                            "minWidth": "320px",
                        },
                    ),
                    # Right card: Tenant Management
                    html.Div(
                        [
                            html.H3(
                                "Tenant Management",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": "20px",
                                    "marginTop": 0,
                                },
                            ),
                            _tenant_table(),
                        ],
                        className="card",
                        style={
                            "padding": f"{PADDING_CARD}px",
                            "background": BG_CARD,
                            "borderRadius": CARD_RADIUS,
                            "boxShadow": CARD_SHADOW,
                            "flex": 1,
                            "minWidth": "320px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": f"{GAP_ELEMENT}px",
                    "alignItems": "flex-start",
                    "flexWrap": "wrap",
                },
            ),
            # -- Danger Zone ------------------------------------
            dcc.ConfirmDialog(
                id="admin-confirm-clear-bookings",
                message="Clear all bookings? This cannot be undone.",
            ),
            html.Div(
                [
                    html.H3(
                        "Danger Zone",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": "#FF3B30",
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.P(
                        "These actions are destructive and cannot be reversed.",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                            "marginBottom": "16px",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "Regenerate synthetic data",
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": 500,
                                            "color": TEXT_PRIMARY,
                                        },
                                    ),
                                    html.Span(
                                        "Replaces all 30 days of data with "
                                        "a new random seed.",
                                        style={
                                            "fontSize": "12px",
                                            "color": TEXT_TERTIARY,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "2px",
                                    "flex": "1",
                                },
                            ),
                            html.Button(
                                "Regenerate Data",
                                id="admin-regen-btn",
                                className="btn-danger",
                                style={
                                    "padding": "8px 20px",
                                    "background": "#FFFFFF",
                                    "color": "#FF3B30",
                                    "border": "1px solid #FF3B30",
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 600,
                                    "cursor": "pointer",
                                    "fontFamily": FONT_STACK,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "16px",
                            "padding": "12px 0",
                            "borderBottom": "1px solid #FFE5E3",
                        },
                    ),
                    html.Div(
                        id="admin-regen-status",
                        style={"marginTop": "8px", "marginBottom": "12px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "Clear all bookings",
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": 500,
                                            "color": TEXT_PRIMARY,
                                        },
                                    ),
                                    html.Span(
                                        "Removes all room bookings from memory.",
                                        style={
                                            "fontSize": "12px",
                                            "color": TEXT_TERTIARY,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "2px",
                                    "flex": "1",
                                },
                            ),
                            html.Button(
                                "Clear Bookings",
                                id="admin-clear-bookings-btn",
                                style={
                                    "padding": "8px 20px",
                                    "background": "#FFFFFF",
                                    "color": "#FF3B30",
                                    "border": "1px solid #FF3B30",
                                    "borderRadius": "8px",
                                    "fontSize": "13px",
                                    "fontWeight": 600,
                                    "cursor": "pointer",
                                    "fontFamily": FONT_STACK,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "16px",
                            "padding": "12px 0",
                        },
                    ),
                    html.Div(
                        id="admin-clear-bookings-status",
                        style={"marginTop": "8px"},
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                    "border": "1px solid #FFE5E3",
                },
            ),
            # -- System Health ----------------------------------
            html.Div(
                [
                    html.H3(
                        "System Health",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        id="admin-system-health",
                        children=html.Span(
                            "Loading system health...",
                            style={
                                "color": TEXT_TERTIARY,
                                "fontSize": "13px",
                            },
                        ),
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Privacy & Data Policy -----------------------------
            html.Div(
                [
                    html.H3(
                        "Privacy & Data Policy",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.P(
                        "PlantaOS processes building sensor data locally. "
                        "Occupancy data uses anonymous counts only. "
                        "No personal identification data is collected "
                        "or transmitted.",
                        style={
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                            "lineHeight": "1.6",
                            "marginBottom": "12px",
                        },
                    ),
                    html.Ul(
                        [
                            html.Li(
                                "Data minimization: Occupancy data uses "
                                "anonymous counts only. No personal "
                                "identification."
                            ),
                            html.Li(
                                "Data retention: 30 days (synthetic). "
                                "Configurable per deployment."
                            ),
                            html.Li(
                                "System guidance queries are anonymized "
                                "\u2014 no PII transmitted"
                            ),
                            html.Li(
                                "Data stored in-memory only, no persistent database"
                            ),
                        ],
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                            "lineHeight": "1.8",
                            "paddingLeft": "20px",
                        },
                    ),
                    # Camera policy toggle
                    html.Div(
                        [
                            html.Div(
                                [
                                    DashIconify(
                                        icon="mdi:camera-off-outline",
                                        width=18,
                                        color=TEXT_TERTIARY,
                                    ),
                                    html.Span(
                                        "Camera Integration",
                                        style={
                                            "fontWeight": 500,
                                            "fontSize": "14px",
                                            "color": TEXT_PRIMARY,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "8px",
                                },
                            ),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        id="admin-camera-toggle",
                                        options=[
                                            {
                                                "label": " Enabled",
                                                "value": "enabled",
                                            },
                                        ],
                                        value=[],
                                        style={"fontSize": "13px"},
                                    ),
                                    html.Span(
                                        "Disabled. If enabled, only derived "
                                        "metadata is stored. No images or "
                                        "video are retained.",
                                        style={
                                            "fontSize": "12px",
                                            "color": TEXT_TERTIARY,
                                            "marginTop": "4px",
                                        },
                                    ),
                                ],
                            ),
                        ],
                        style={
                            "padding": "12px 0",
                            "borderTop": "1px solid #E5E5EA",
                            "marginTop": "8px",
                        },
                    ),
                    # Data Access Levels
                    html.Div(
                        [
                            html.Span(
                                "Data Access Levels",
                                style={
                                    "fontWeight": 600,
                                    "fontSize": "14px",
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("Role"),
                                                html.Th("Access"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(
                                        [
                                            html.Tr(
                                                [
                                                    html.Td("Admin"),
                                                    html.Td(
                                                        "Full system configuration"
                                                    ),
                                                ]
                                            ),
                                            html.Tr(
                                                [
                                                    html.Td("Operator"),
                                                    html.Td(
                                                        "View all data, manage bookings"
                                                    ),
                                                ]
                                            ),
                                            html.Tr(
                                                [
                                                    html.Td("Viewer"),
                                                    html.Td("Dashboard view only"),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "width": "100%",
                                    "borderCollapse": "collapse",
                                    "marginTop": "8px",
                                    "fontSize": "13px",
                                },
                            ),
                        ],
                        style={
                            "marginTop": "16px",
                            "borderTop": "1px solid #E5E5EA",
                            "paddingTop": "12px",
                        },
                    ),
                    html.P(
                        "GDPR Compliance: System designed for GDPR "
                        "compliance. Contact admin for data requests. "
                        "dpo@plantaos.com",
                        style={
                            "fontSize": "12px",
                            "color": TEXT_TERTIARY,
                            "marginTop": "16px",
                        },
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Operating Principles ------------------------------
            html.Div(
                [
                    html.H3(
                        "Operating Principles",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.P(
                        "System rules governing automated recommendations and alerts.",
                        style={
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                            "lineHeight": "1.6",
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(
                        [
                            _principle_row(
                                "Comfort Thresholds",
                                "Temperature 20\u201324\u00b0C, "
                                "CO\u2082 < 800 ppm, "
                                "Humidity 40\u201360%",
                            ),
                            _principle_row(
                                "Alert Triggers",
                                "Temperature deviation > 2\u00b0C, "
                                "CO\u2082 > 1000 ppm, "
                                "Occupancy > 90% capacity",
                            ),
                            _principle_row(
                                "Scoring Formula",
                                "Zone health = f(temperature, CO\u2082, "
                                "humidity, occupancy, energy)",
                            ),
                            _principle_row(
                                "Adaptive Baselines",
                                "Rolling 7-day average per zone per "
                                "15-min interval. Anomalies flagged "
                                "above 2\u03c3.",
                            ),
                            _principle_row(
                                "Booking Priority",
                                "Room scoring: 45% comfort projection + "
                                "35% energy efficiency + "
                                "20% capacity fit",
                            ),
                        ]
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Key Management --------------------------------
            html.Div(
                [
                    html.H3(
                        "Key Management",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "Anthropic API",
                                        style={
                                            "fontWeight": 500,
                                            "fontSize": "14px",
                                            "color": TEXT_PRIMARY,
                                        },
                                    ),
                                    html.Span(
                                        "Used for operational intelligence "
                                        "and building insights.",
                                        style={
                                            "fontSize": "12px",
                                            "color": TEXT_TERTIARY,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "2px",
                                    "flex": "1",
                                },
                            ),
                            html.Div(
                                id="admin-api-status-badge",
                                children=_build_api_status_badge(),
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "16px",
                            "padding": "10px 0",
                        },
                    ),
                    html.P(
                        "API keys are never displayed. Only connection "
                        "status is shown. Configure keys via environment "
                        "variables or the Pricing & Integration card above.",
                        style={
                            "fontSize": "12px",
                            "color": TEXT_TERTIARY,
                            "marginTop": "8px",
                        },
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Audit Log Viewer --------------------------------
            dcc.ConfirmDialog(
                id="admin-confirm-clear-audit",
                message=("Clear the audit log? This cannot be undone."),
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Audit Log",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": 0,
                                    "marginTop": 0,
                                },
                            ),
                            html.Button(
                                "Clear Log",
                                id="admin-clear-audit-btn",
                                style={
                                    "padding": "6px 14px",
                                    "background": "#FFFFFF",
                                    "color": TEXT_TERTIARY,
                                    "border": f"1px solid {TEXT_TERTIARY}",
                                    "borderRadius": "8px",
                                    "fontSize": "12px",
                                    "fontWeight": 500,
                                    "cursor": "pointer",
                                    "fontFamily": FONT_STACK,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(
                        id="admin-audit-log-viewer",
                        children=html.Span(
                            "No audit entries yet. Actions like sensor "
                            "changes, tenant switches, and exports are "
                            "logged here.",
                            style={
                                "color": TEXT_TERTIARY,
                                "fontSize": "13px",
                            },
                        ),
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Role Concept (MVP simple) -------------------------
            html.Div(
                [
                    html.H3(
                        "Access Control",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:shield-account-outline",
                                width=20,
                                color=ACCENT_BLUE,
                            ),
                            html.Span(
                                "Current role: Admin",
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": 500,
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Span(
                                "Admin",
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": 500,
                                    "color": ACCENT_BLUE,
                                    "padding": "2px 10px",
                                    "borderRadius": "8px",
                                    "background": "#E8F5EE",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "marginBottom": "16px",
                        },
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                id="admin-require-password",
                                options=[
                                    {
                                        "label": (
                                            " Require password for destructive actions"
                                        ),
                                        "value": "require_password",
                                    },
                                ],
                                value=[],
                                style={"fontSize": "13px"},
                            ),
                            html.Span(
                                "When enabled, data regeneration and "
                                "booking clears will require confirmation "
                                "with a password.",
                                style={
                                    "fontSize": "12px",
                                    "color": TEXT_TERTIARY,
                                    "marginTop": "4px",
                                    "display": "block",
                                },
                            ),
                        ],
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
            # -- Architecture & Integrity -----------------------
            html.Div(
                [
                    html.H3(
                        "Architecture & Integrity",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.P(
                        "Runtime stack information and dependency inventory.",
                        style={
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                            "marginBottom": "16px",
                        },
                    ),
                    html.Div(
                        id="admin-integrity-content",
                        children=html.Span(
                            "Loading integrity data...",
                            style={
                                "color": TEXT_TERTIARY,
                                "fontSize": "13px",
                            },
                        ),
                    ),
                ],
                className="card",
                style={
                    "padding": f"{PADDING_CARD}px",
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "marginTop": f"{GAP_ELEMENT}px",
                },
            ),
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
            "fontFamily": FONT_STACK,
        },
    )
