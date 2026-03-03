"""Insights page callbacks.

Registers callbacks for insight generation, feed rendering,
chat interaction, and summary display on the insights page.
"""

from __future__ import annotations

from datetime import datetime

from dash import Input, Output, State, ctx, html, no_update
from dash_iconify import DashIconify
from loguru import logger

from config.theme import ACCENT_BLUE, TEXT_TERTIARY
from core.insights import (
    answer_building_question,
    generate_building_insights,
    state_has_changed,
)
from views.components.insight_card import create_insight_card


def register_insights_callbacks(app: object) -> None:
    """Register all insights page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_insight_generation(app)
    _register_insight_feed(app)
    _register_chat_send(app)
    _register_chat_render(app)


def _register_insight_generation(app: object) -> None:
    """Generate new insights when building state changes."""

    @app.callback(
        Output("insights-store", "data"),
        Input("insights-refresh-interval", "n_intervals"),
        Input("building-state-store", "data"),
        State("insights-store", "data"),
    )
    def generate_insights(
        _n: int,
        state_data: dict | None,
        existing_insights: list | None,
    ) -> list:
        """Scan building state and generate insights."""
        if existing_insights is None:
            existing_insights = []

        if not state_data:
            return existing_insights

        # Check if state changed significantly
        if not state_has_changed(state_data):
            return no_update

        logger.debug("Building state changed, generating insights")

        try:
            new_insights = generate_building_insights(state_data)
        except Exception as e:
            logger.warning(f"Insight generation failed: {e}")
            return existing_insights

        # Convert to dicts and prepend
        new_dicts = [i.model_dump() for i in new_insights]
        combined = new_dicts + existing_insights

        # Keep max 100
        return combined[:100]


def _register_insight_feed(app: object) -> None:
    """Render insight cards from store with filtering."""

    @app.callback(
        Output("insights-feed", "children"),
        Output("insights-summary", "children"),
        Input("insights-store", "data"),
        Input("insights-severity-filter", "value"),
        Input("insights-zone-filter", "value"),
    )
    def render_feed(
        insights_data: list | None,
        severity_filter: str,
        zone_filter: list[str] | None,
    ) -> tuple[list, list]:
        """Filter and render insight cards + summary strip."""
        if not insights_data:
            empty = html.Div(
                [
                    DashIconify(
                        icon="mdi:shield-check-outline",
                        width=48,
                        color=TEXT_TERTIARY,
                    ),
                    html.Div(
                        "No insights yet",
                        style={
                            "fontSize": "16px",
                            "fontWeight": 500,
                            "marginTop": "12px",
                        },
                    ),
                    html.Div(
                        "PlantaOS is monitoring the building and will "
                        "generate insights when anomalies are detected.",
                        style={
                            "color": TEXT_TERTIARY,
                            "fontSize": "13px",
                            "marginTop": "4px",
                        },
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "48px 24px",
                },
            )
            summary = _build_summary_strip(0, 0, 0)
            return [empty], summary

        # Apply filters
        filtered = insights_data
        if severity_filter and severity_filter != "all":
            filtered = [i for i in filtered if i.get("severity") == severity_filter]
        if zone_filter:
            zone_set = set(zone_filter)
            filtered = [
                i for i in filtered if zone_set & set(i.get("affected_zones", []))
            ]

        # Build summary from all (unfiltered) insights
        today_str = datetime.now().date().isoformat()
        today_insights = [
            i for i in insights_data if i.get("timestamp", "").startswith(today_str)
        ]
        total = len(today_insights)
        critical = sum(1 for i in today_insights if i.get("severity") == "critical")
        warnings = sum(1 for i in today_insights if i.get("severity") == "warning")

        summary = _build_summary_strip(total, critical, warnings)

        # Render cards
        if not filtered:
            empty = html.Div(
                "No insights match the current filters.",
                style={
                    "color": TEXT_TERTIARY,
                    "textAlign": "center",
                    "padding": "32px",
                },
            )
            return [empty], summary

        cards = [create_insight_card(insight=i) for i in filtered]
        return cards, summary


def _build_summary_strip(total: int, critical: int, warnings: int) -> list:
    """Build the summary statistics strip.

    Args:
        total: Total insights today.
        critical: Number of critical insights.
        warnings: Number of warning insights.

    Returns:
        List of Dash components for the summary strip.
    """
    return [
        html.Div(
            [
                DashIconify(icon="mdi:lightbulb-on", width=16, color=ACCENT_BLUE),
                html.Span(
                    f"{total} Insight{'s' if total != 1 else ''} Today",
                    style={"fontWeight": 500},
                ),
            ],
            className="summary-badge",
        ),
        html.Div(
            [
                DashIconify(icon="mdi:alert-circle", width=16, color="#FF3B30"),
                html.Span(
                    f"{critical} Critical",
                    style={"fontWeight": 500, "color": "#FF3B30"},
                ),
            ],
            className="summary-badge",
        ),
        html.Div(
            [
                DashIconify(icon="mdi:alert-outline", width=16, color="#FF9500"),
                html.Span(
                    f"{warnings} Warning{'s' if warnings != 1 else ''}",
                    style={"fontWeight": 500, "color": "#FF9500"},
                ),
            ],
            className="summary-badge",
        ),
    ]


def _register_chat_send(app: object) -> None:
    """Handle sending chat messages and getting AI responses."""

    @app.callback(
        Output("chat-store", "data"),
        Output("chat-input", "value"),
        Input("chat-send-btn", "n_clicks"),
        Input("chat-input", "n_submit"),
        State("chat-input", "value"),
        State("building-state-store", "data"),
        State("chat-store", "data"),
    )
    def send_chat(
        n_clicks: int,
        n_submit: int,
        question: str | None,
        state_data: dict | None,
        chat_history: list | None,
    ) -> tuple[list, str]:
        """Process user question and get AI response."""
        if chat_history is None:
            chat_history = []

        # Only proceed if button clicked or enter pressed with text
        if not question or not question.strip():
            return no_update, no_update

        # Prevent processing on initial load
        triggered = ctx.triggered_id
        if triggered not in ("chat-send-btn", "chat-input"):
            return no_update, no_update

        question = question.strip()
        now_str = datetime.now().isoformat()

        # Add user message
        chat_history.append({"role": "user", "text": question, "timestamp": now_str})

        # Get AI response
        response = answer_building_question(question, state_data)

        # Add assistant response
        chat_history.append(
            {
                "role": "assistant",
                "text": response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep max 50 messages
        chat_history = chat_history[-50:]

        return chat_history, ""


def _register_chat_render(app: object) -> None:
    """Render chat messages from store."""

    @app.callback(
        Output("chat-messages", "children"),
        Input("chat-store", "data"),
    )
    def render_chat(chat_data: list | None) -> list:
        """Map chat history to bubble components."""
        if not chat_data:
            return [
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
                )
            ]

        bubbles = []
        for msg in chat_data:
            role = msg.get("role", "user")
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            # Format timestamp
            try:
                ts_dt = datetime.fromisoformat(ts)
                ts_str = ts_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                ts_str = ""

            if role == "user":
                bubble = html.Div(
                    [
                        html.Div(text, className="chat-bubble-text"),
                        html.Div(
                            ts_str,
                            className="chat-bubble-time",
                        ),
                    ],
                    className="chat-bubble user",
                )
            else:
                bubble = html.Div(
                    [
                        html.Div(
                            [
                                DashIconify(
                                    icon="mdi:robot-outline",
                                    width=14,
                                    color=ACCENT_BLUE,
                                ),
                                html.Span(
                                    "PlantaOS",
                                    style={
                                        "fontSize": "11px",
                                        "fontWeight": 600,
                                        "color": ACCENT_BLUE,
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "4px",
                                "marginBottom": "4px",
                            },
                        ),
                        html.Div(text, className="chat-bubble-text"),
                        html.Div(
                            ts_str,
                            className="chat-bubble-time",
                        ),
                    ],
                    className="chat-bubble assistant",
                )

            bubbles.append(bubble)

        return bubbles
