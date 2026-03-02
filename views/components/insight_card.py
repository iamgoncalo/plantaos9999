"""AI insight display card with explanation.

Renders AI-generated insights with context, severity level,
and actionable recommendations.
"""

from __future__ import annotations

from datetime import datetime

from dash import html


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
    ...
