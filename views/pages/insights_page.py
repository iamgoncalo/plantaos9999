"""Insights page: AI insight feed and chat interface.

Displays AI-generated insights about building operations powered
by Claude API, with an interactive chat interface for asking
questions about building state and anomalies.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.building import get_monitored_zones
from config.theme import ACCENT_BLUE, TEXT_SECONDARY, TEXT_TERTIARY


def create_insights_page() -> html.Div:
    """Create the AI insights page layout.

    Returns:
        Dash html.Div containing the insights feed, filters,
        summary strip, and chat interface.
    """
    # Zone options for filter dropdown
    zone_options = [{"label": z.name, "value": z.id} for z in get_monitored_zones()]

    return html.Div(
        [
            # ── Stores + Interval ────────────────────
            dcc.Store(id="insights-store", storage_type="session", data=[]),
            dcc.Store(id="chat-store", storage_type="session", data=[]),
            dcc.Interval(
                id="insights-refresh-interval",
                interval=5 * 60 * 1000,  # 5 minutes
                n_intervals=0,
            ),
            # ── Header Row ───────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:lightbulb-on-outline",
                                width=24,
                                color=ACCENT_BLUE,
                            ),
                            html.H2(
                                "System Intelligence",
                                style={
                                    "margin": 0,
                                    "fontSize": "20px",
                                    "fontWeight": 600,
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
                            dcc.Dropdown(
                                id="insights-severity-filter",
                                options=[
                                    {"label": "All Severities", "value": "all"},
                                    {"label": "Critical", "value": "critical"},
                                    {"label": "Warning", "value": "warning"},
                                    {"label": "Info", "value": "info"},
                                ],
                                value="all",
                                clearable=False,
                                className="zone-filter",
                                style={"minWidth": "150px"},
                            ),
                            dcc.Dropdown(
                                id="insights-zone-filter",
                                options=zone_options,
                                multi=True,
                                placeholder="All zones",
                                className="zone-filter",
                                style={"minWidth": "220px"},
                            ),
                        ],
                        className="page-controls",
                    ),
                ],
                className="page-controls",
                style={"justifyContent": "space-between"},
            ),
            # ── Summary Strip ────────────────────────
            html.Div(id="insights-summary", className="insights-summary"),
            # ── Two-Column Layout ────────────────────
            html.Div(
                [
                    # Left: Insights Feed
                    html.Div(
                        [
                            html.Div(
                                "PlantaOS is analyzing building data...",
                                className="empty-state",
                                style={
                                    "color": TEXT_TERTIARY,
                                    "padding": "32px",
                                    "textAlign": "center",
                                },
                            ),
                        ],
                        id="insights-feed",
                        className="insights-feed",
                    ),
                    # Right: Ask PlantaOS Chat
                    html.Div(
                        [
                            html.Div(
                                [
                                    DashIconify(
                                        icon="mdi:robot-outline",
                                        width=20,
                                        color=ACCENT_BLUE,
                                    ),
                                    html.Span(
                                        "Ask PlantaOS",
                                        style={
                                            "fontSize": "15px",
                                            "fontWeight": 600,
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "8px",
                                    "marginBottom": "4px",
                                },
                            ),
                            html.Div(
                                "Ask questions about building operations",
                                style={
                                    "color": TEXT_SECONDARY,
                                    "fontSize": "13px",
                                    "marginBottom": "16px",
                                },
                            ),
                            # Chat messages area
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            DashIconify(
                                                icon="mdi:message-text-outline",
                                                width=32,
                                                color=TEXT_TERTIARY,
                                            ),
                                            html.Div(
                                                "Ask a question to get started",
                                                style={
                                                    "color": TEXT_TERTIARY,
                                                    "fontSize": "13px",
                                                    "marginTop": "8px",
                                                },
                                            ),
                                        ],
                                        style={
                                            "textAlign": "center",
                                            "padding": "40px 16px",
                                        },
                                    ),
                                ],
                                id="chat-messages",
                                className="chat-messages",
                            ),
                            # Chat input
                            html.Div(
                                [
                                    dcc.Input(
                                        id="chat-input",
                                        type="text",
                                        placeholder="Ask about the building...",
                                        className="chat-text-input",
                                        debounce=True,
                                        n_submit=0,
                                    ),
                                    html.Button(
                                        [
                                            DashIconify(
                                                icon="mdi:send",
                                                width=18,
                                                color="#FFFFFF",
                                            ),
                                        ],
                                        id="chat-send-btn",
                                        className="chat-send-btn",
                                        n_clicks=0,
                                    ),
                                ],
                                className="chat-input-row",
                            ),
                        ],
                        className="card chat-panel",
                    ),
                ],
                className="insights-layout",
            ),
        ],
        className="page-enter",
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "16px",
        },
    )
