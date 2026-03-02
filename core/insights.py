"""AI-powered insights via Claude API.

Sends anomaly context and building state to the Anthropic API
and returns natural language explanations and recommendations.
Falls back to template-based insights if the API is unavailable.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from loguru import logger


def generate_insight(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Generate a natural language insight for an anomaly.

    Sends context to Claude API and returns an explanation with
    recommendations. Falls back to a template if API is unavailable.

    Args:
        anomaly: Dict describing the anomaly (zone, metric, value,
            baseline, severity, etc.).
        context: Optional building-wide context for richer insights.

    Returns:
        Natural language insight string.
    """
    ...


def generate_daily_summary(target_date: date | None = None) -> str:
    """Generate a natural language summary for a day.

    Args:
        target_date: Date to summarize. Defaults to today.

    Returns:
        Summary string with key findings and recommendations.
    """
    ...


def generate_zone_analysis(zone_id: str) -> str:
    """Generate a detailed analysis for a specific zone.

    Args:
        zone_id: Zone to analyze.

    Returns:
        Analysis string with metrics, trends, and recommendations.
    """
    ...


def _build_prompt(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Construct the prompt for the Claude API.

    Args:
        anomaly: Anomaly details.
        context: Building context.

    Returns:
        Formatted prompt string.
    """
    ...


def _call_claude_api(prompt: str) -> str:
    """Call the Anthropic Claude API.

    Args:
        prompt: The prompt to send.

    Returns:
        Response text from Claude.
    """
    ...


def _fallback_insight(anomaly: dict[str, Any]) -> str:
    """Generate a template-based insight when API is unavailable.

    Args:
        anomaly: Anomaly details.

    Returns:
        Template-based insight string.
    """
    ...
