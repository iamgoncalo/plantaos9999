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
            dcc.Store(id="admin-settings-store", storage_type="session"),
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
            # -- Bottom card: Data Management ---------------------
            html.Div(
                [
                    html.H3(
                        "Data Management",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "12px",
                            "marginTop": 0,
                        },
                    ),
                    html.P(
                        "Current data: 30 days of synthetic readings",
                        style={
                            "fontSize": "14px",
                            "color": TEXT_SECONDARY,
                            "marginBottom": "16px",
                        },
                    ),
                    html.Button(
                        "Regenerate Data",
                        id="admin-regen-btn",
                        className="btn-primary",
                    ),
                    html.Div(
                        id="admin-regen-status",
                        style={"marginTop": "12px"},
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
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": f"{GAP_ELEMENT}px",
            "fontFamily": FONT_STACK,
        },
    )
