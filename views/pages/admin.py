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
                        "No personal identification data is collected or "
                        "transmitted. Occupancy data is zone-level aggregate "
                        "counts only.",
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
                                "Sensor data retained for 30 days, "
                                "then automatically purged"
                            ),
                            html.Li(
                                "Occupancy: aggregate zone-level counts "
                                "only, no individual tracking"
                            ),
                            html.Li(
                                "System guidance queries are anonymized "
                                "\u2014 no PII transmitted"
                            ),
                            html.Li(
                                "Data stored in-memory only, no persistent database"
                            ),
                            html.Li(
                                "Camera systems: not deployed "
                                "(policy: no visual surveillance)"
                            ),
                        ],
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                            "lineHeight": "1.8",
                            "paddingLeft": "20px",
                        },
                    ),
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
                        "GDPR Compliance: All data processing complies "
                        "with EU GDPR. Contact: dpo@plantaos.com",
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
                                "Temperature 20-24\u00b0C, Humidity 40-60%, "
                                "CO\u2082 <1000 ppm, Light 300-500 lux",
                            ),
                            _principle_row(
                                "Alert Triggers",
                                "Zone status moves to 'warning' when any "
                                "metric exceeds \u00b11\u03c3 from baseline. "
                                "'Critical' at \u00b12\u03c3.",
                            ),
                            _principle_row(
                                "Scoring Formula",
                                "Zone Performance = 0.35 \u00d7 Comfort + "
                                "0.30 \u00d7 Energy Efficiency + "
                                "0.20 \u00d7 Utilization + "
                                "0.15 \u00d7 Safety",
                            ),
                            _principle_row(
                                "Energy Baselines",
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
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
            "fontFamily": FONT_STACK,
        },
    )
