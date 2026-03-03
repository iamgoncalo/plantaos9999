"""AI insight display card with explanation.

Renders AI-generated insights with context, severity level,
and actionable recommendations.
"""

from __future__ import annotations

from datetime import datetime

from dash import html
from dash_iconify import DashIconify

from config.theme import ACCENT_BLUE


def create_insight_card(
    insight: str,
    category: str = "general",
    timestamp: datetime | None = None,
    severity: str = "info",
    zone_id: str | None = None,
) -> html.Div:
    """Create an AI insight card component.

    Args:
        insight: The insight text content.
        category: Insight category (e.g., 'energy', 'comfort', 'anomaly').
        timestamp: When the insight was generated.
        severity: Severity level ('info', 'warning', 'critical').
        zone_id: Related zone identifier.

    Returns:
        Dash html.Div with insight card layout.
    """
    header_children: list = [
        DashIconify(icon="mdi:lightbulb-on", width=16, color=ACCENT_BLUE),
        html.Span(category.upper(), className=f"insight-category {category}"),
    ]

    if timestamp:
        ts_str = timestamp.strftime("%H:%M · %d %b")
        header_children.append(html.Span(ts_str, className="insight-timestamp"))

    if zone_id:
        header_children.append(html.Span(zone_id, className="insight-zone-badge"))

    header = html.Div(header_children, className="insight-header")

    body = html.Div(insight, className="insight-body")

    severity_class = severity if severity in ("warning", "critical") else ""
    card_class = f"insight-card {severity_class}".strip()

    return html.Div(
        [header, body],
        className=card_class,
    )
