"""Deployment page: admin god-mode for AFI formula tuning and sensor deployment.

Provides real-time sliders for adjusting AFI engine parameters (financial
rates, distortion weights) and previews the impact on Freedom scores and
financial bleed across all monitored zones.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.afi_config import DEFAULT_AFI_CONFIG
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


def _slider_row(
    label: str,
    slider_id: str,
    min_val: float,
    max_val: float,
    step: float,
    value: float,
    unit: str = "",
) -> html.Div:
    """Create a labeled slider row for formula tuning.

    Args:
        label: Display label for the slider.
        slider_id: Dash component ID.
        min_val: Minimum slider value.
        max_val: Maximum slider value.
        step: Slider step increment.
        value: Default slider value.
        unit: Optional unit suffix for display.

    Returns:
        html.Div containing label and slider.
    """
    display_label = f"{label} ({unit})" if unit else label
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        display_label,
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                            "fontWeight": 500,
                        },
                    ),
                    html.Span(
                        f"{value}",
                        id=f"{slider_id}-display",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_TERTIARY,
                            "fontFamily": "JetBrains Mono",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "marginBottom": "4px",
                },
            ),
            dcc.Slider(
                id=slider_id,
                min=min_val,
                max=max_val,
                step=step,
                value=value,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ],
        style={"marginBottom": "16px"},
    )


def create_deployment_page() -> html.Div:
    """Create the deployment and configuration admin page layout.

    Returns:
        Dash html.Div containing formula tuning sliders,
        impact preview panel, and sensor deployment map.
    """
    cfg = DEFAULT_AFI_CONFIG

    return html.Div(
        [
            # -- Header ----------------------------------------
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
                                "Deployment",
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
                        "Plan your sensor deployment, tune building parameters, "
                        "and calculate ROI.",
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
            # -- Hidden config store --------------------------
            dcc.Store(id="deploy-afi-config-store"),
            # -- Two-column layout -----------------------------
            html.Div(
                [
                    # Left column: Formula Tuning
                    html.Div(
                        [
                            html.H3(
                                "Building Parameters",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": "20px",
                                    "marginTop": 0,
                                },
                            ),
                            _slider_row(
                                "Energy Cost",
                                "deploy-cost-slider",
                                0.05,
                                0.30,
                                0.01,
                                cfg.cost_per_kwh,
                                unit="\u20ac/kWh",
                            ),
                            _slider_row(
                                "Average Hourly Wage",
                                "deploy-wage-slider",
                                8.0,
                                25.0,
                                0.5,
                                cfg.avg_hourly_wage,
                                unit="\u20ac/hr",
                            ),
                            _slider_row(
                                "Temperature Sensitivity",
                                "deploy-w-temp",
                                0.0,
                                1.0,
                                0.05,
                                cfg.w_temperature,
                            ),
                            _slider_row(
                                "Air Quality Sensitivity",
                                "deploy-w-co2",
                                0.0,
                                1.0,
                                0.05,
                                cfg.w_co2,
                            ),
                            _slider_row(
                                "Crowding Sensitivity",
                                "deploy-w-crowd",
                                0.0,
                                1.0,
                                0.05,
                                cfg.w_crowding,
                            ),
                            _slider_row(
                                "Exit Access Sensitivity",
                                "deploy-w-exit",
                                0.0,
                                1.0,
                                0.05,
                                cfg.w_blocked_exit,
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
                    # Right column: Impact Preview
                    html.Div(
                        [
                            html.H3(
                                "Impact Preview",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                    "marginBottom": "20px",
                                    "marginTop": 0,
                                },
                            ),
                            # Before/after comparison container
                            html.Div(
                                "Adjust parameters to preview the impact on "
                                "building health and operating cost.",
                                id="deploy-impact-preview",
                                style={
                                    "fontSize": "13px",
                                    "color": TEXT_SECONDARY,
                                    "minHeight": "180px",
                                },
                            ),
                            html.Hr(
                                style={
                                    "border": "none",
                                    "borderTop": "1px solid #E5E5EA",
                                    "margin": "16px 0",
                                },
                            ),
                            # Sensor placement map
                            html.Div(
                                [
                                    html.Div(
                                        "Sensor Placement Map",
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": 600,
                                            "color": TEXT_PRIMARY,
                                            "marginBottom": "8px",
                                        },
                                    ),
                                    dcc.Graph(
                                        id="deploy-sensor-map",
                                        config={
                                            "displaylogo": False,
                                            "displayModeBar": False,
                                        },
                                        style={"height": "300px"},
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
            # ── ROI Calculator Section ────────────
            html.Div(
                [
                    html.H3(
                        "ROI Calculator",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "16px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Number of Sensors",
                                        style={
                                            "fontSize": "13px",
                                            "fontWeight": 500,
                                            "color": TEXT_SECONDARY,
                                            "marginBottom": "4px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Input(
                                        id="deploy-sensor-count",
                                        type="number",
                                        value=16,
                                        min=1,
                                        max=100,
                                        style={
                                            "width": "100%",
                                            "padding": "8px 12px",
                                            "borderRadius": "8px",
                                            "border": "1px solid #E5E5EA",
                                            "fontSize": "14px",
                                            "fontFamily": "JetBrains Mono",
                                        },
                                    ),
                                ],
                                style={"flex": 1, "minWidth": "140px"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Cost per Sensor (€)",
                                        style={
                                            "fontSize": "13px",
                                            "fontWeight": 500,
                                            "color": TEXT_SECONDARY,
                                            "marginBottom": "4px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Input(
                                        id="deploy-sensor-cost",
                                        type="number",
                                        value=150,
                                        min=10,
                                        max=2000,
                                        style={
                                            "width": "100%",
                                            "padding": "8px 12px",
                                            "borderRadius": "8px",
                                            "border": "1px solid #E5E5EA",
                                            "fontSize": "14px",
                                            "fontFamily": "JetBrains Mono",
                                        },
                                    ),
                                ],
                                style={"flex": 1, "minWidth": "140px"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Installation Cost (€)",
                                        style={
                                            "fontSize": "13px",
                                            "fontWeight": 500,
                                            "color": TEXT_SECONDARY,
                                            "marginBottom": "4px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Input(
                                        id="deploy-install-cost",
                                        type="number",
                                        value=2000,
                                        min=0,
                                        max=50000,
                                        style={
                                            "width": "100%",
                                            "padding": "8px 12px",
                                            "borderRadius": "8px",
                                            "border": "1px solid #E5E5EA",
                                            "fontSize": "14px",
                                            "fontFamily": "JetBrains Mono",
                                        },
                                    ),
                                ],
                                style={"flex": 1, "minWidth": "140px"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "16px",
                            "marginBottom": "20px",
                            "flexWrap": "wrap",
                        },
                    ),
                    html.Div(
                        id="deploy-roi-summary",
                        children=html.Span(
                            "Enter values above to calculate ROI.",
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
                },
            ),
            # ── CapEx vs OpEx Summary ──────────────
            html.Div(
                [
                    html.H3(
                        "CapEx vs OpEx Summary",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                            "marginBottom": "16px",
                            "marginTop": 0,
                        },
                    ),
                    html.Div(
                        id="deploy-capex-opex",
                        children=html.Span(
                            "ROI data will appear here when sensor inputs are provided.",
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
