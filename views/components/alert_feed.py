"""Scrolling alert list component.

Displays a live-updating list of building alerts and anomalies,
color-coded by severity (info, warning, critical).
"""

from __future__ import annotations

from dash import html


def create_alert_feed(
    alerts: list[dict] | None = None,
    max_items: int = 10,
) -> html.Div:
    """Create the alert feed component.

    Args:
        alerts: List of alert dicts with keys: message, severity,
            timestamp, zone_id.
        max_items: Maximum alerts to display.

    Returns:
        Dash html.Div with scrolling alert list.
    """
    ...


def _create_alert_item(alert: dict) -> html.Div:
    """Create a single alert list item.

    Args:
        alert: Alert dict with message, severity, timestamp, zone_id.

    Returns:
        Dash html.Div for one alert item.
    """
    ...
