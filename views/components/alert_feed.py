"""Scrolling alert list component.

Displays a live-updating list of building alerts and anomalies,
color-coded by severity (info, warning, critical).
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import (
    STATUS_CRITICAL,
    STATUS_INFO,
    STATUS_WARNING,
    TEXT_TERTIARY,
)

_SEVERITY_ICONS: dict[str, tuple[str, str]] = {
    "critical": ("mdi:alert-circle", STATUS_CRITICAL),
    "warning": ("mdi:alert", STATUS_WARNING),
    "info": ("mdi:information", STATUS_INFO),
}


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
    header = html.Div(
        [
            html.Span("Recent Alerts"),
            html.Span(
                f"{len(alerts) if alerts else 0}",
                style={
                    "fontSize": "11px",
                    "color": TEXT_TERTIARY,
                },
            ),
        ],
        className="alert-feed-header",
    )

    if not alerts:
        body = html.Div(
            [
                DashIconify(
                    icon="mdi:check-circle-outline",
                    width=32,
                    color=TEXT_TERTIARY,
                ),
                html.Div(
                    "No active alerts",
                    style={"marginTop": "8px"},
                ),
            ],
            className="empty-state",
        )
    else:
        items = [_create_alert_item(a) for a in alerts[:max_items]]
        body = html.Div(items, className="alert-feed-list")

    return html.Div(
        [header, body],
        className="alert-feed",
        id="alert-feed",
    )


def _create_alert_item(alert: dict) -> html.Div:
    """Create a single alert list item.

    Args:
        alert: Alert dict with message, severity, timestamp, zone_id.

    Returns:
        Dash html.Div for one alert item.
    """
    severity = alert.get("severity", "info")
    icon_name, icon_color = _SEVERITY_ICONS.get(
        severity, ("mdi:information", STATUS_INFO)
    )

    item_header = html.Div(
        [
            DashIconify(icon=icon_name, width=16, color=icon_color),
            html.Span(
                alert.get("message", ""),
                className="alert-item-message",
            ),
        ],
        className="alert-item-header",
    )

    meta_children: list = []
    if alert.get("timestamp"):
        meta_children.append(
            html.Span(str(alert["timestamp"]))
        )
    if alert.get("zone_id"):
        meta_children.append(
            html.Span(alert["zone_id"], className="alert-item-zone")
        )

    meta = html.Div(meta_children, className="alert-item-meta")

    return html.Div(
        [item_header, meta],
        className=f"alert-item {severity}",
    )
