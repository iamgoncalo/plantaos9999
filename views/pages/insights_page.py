"""Insights page: AI insight feed and chat interface.

Displays AI-generated insights about building operations powered
by Claude API, with an interactive chat interface for asking
questions about building state and anomalies.
"""

from __future__ import annotations

from datetime import datetime

from dash import html

from config.theme import TEXT_TERTIARY
from views.components.insight_card import create_insight_card


def create_insights_page() -> html.Div:
    """Create the AI insights page layout.

    Returns:
        Dash html.Div containing the insights feed and chat
        interface.
    """
    sample_insights = [
        create_insight_card(
            insight=(
                "HVAC energy consumption has been consistently above "
                "baseline for the past 3 hours in Sala Multiusos. "
                "Consider checking thermostat settings."
            ),
            category="energy",
            timestamp=datetime.now(),
            severity="warning",
            zone_id="p0_sala_multiusos",
        ),
        create_insight_card(
            insight=(
                "Building occupancy patterns today are within expected "
                "ranges. Morning shift peak reached 78% of capacity."
            ),
            category="general",
            timestamp=datetime.now(),
            severity="info",
        ),
    ]

    feed = html.Div(
        sample_insights,
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
        id="insights-feed",
    )

    chat_placeholder = html.Div(
        [
            html.Div(
                "AI Chat Interface",
                style={
                    "fontSize": "15px",
                    "fontWeight": 600,
                    "marginBottom": "16px",
                },
            ),
            html.Div(
                "Ask questions about building operations — "
                "powered by Claude API",
                style={"color": TEXT_TERTIARY, "fontSize": "14px"},
            ),
        ],
        className="card",
        style={"minHeight": "200px"},
        id="insights-chat",
    )

    return html.Div(
        [feed, chat_placeholder],
        className="page-enter",
        style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )
