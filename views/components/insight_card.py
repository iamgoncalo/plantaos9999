"""AI insight display card with explanation.

Renders AI-generated insights with context, severity level,
and actionable recommendations. Supports both plain text insights
and structured Insight dicts with title, zones, and actions.
"""

from __future__ import annotations

from datetime import datetime

from dash import html
from dash_iconify import DashIconify

from config.building import get_zone_by_id
from config.theme import ACCENT_BLUE, TEXT_TERTIARY

# Severity icon mapping
_SEVERITY_ICONS: dict[str, str] = {
    "info": "mdi:information-outline",
    "warning": "mdi:alert-outline",
    "critical": "mdi:alert-circle",
}

_SEVERITY_COLORS: dict[str, str] = {
    "info": ACCENT_BLUE,
    "warning": "#FF9500",
    "critical": "#FF3B30",
}


def create_insight_card(
    insight: str | dict | None = None,
    category: str = "general",
    timestamp: datetime | str | None = None,
    severity: str = "info",
    zone_id: str | None = None,
    *,
    title: str | None = None,
    affected_zones: list[str] | None = None,
    recommended_action: str | None = None,
) -> html.Div:
    """Create an AI insight card component.

    Supports both simple string insights and structured Insight dicts.

    Args:
        insight: The insight text content, or a dict from Insight.model_dump().
        category: Insight category (e.g., 'energy', 'comfort', 'anomaly').
        timestamp: When the insight was generated.
        severity: Severity level ('info', 'warning', 'critical').
        zone_id: Related zone identifier (deprecated, use affected_zones).
        title: Bold title displayed above the explanation.
        affected_zones: List of zone_ids this insight affects.
        recommended_action: Suggested corrective action.

    Returns:
        Dash html.Div with insight card layout.
    """
    # Unpack dict if insight is a full Insight dict
    if isinstance(insight, dict):
        title = title or insight.get("title")
        explanation = insight.get("explanation", "")
        category = insight.get("category", category)
        severity = insight.get("severity", severity)
        affected_zones = affected_zones or insight.get("affected_zones", [])
        recommended_action = recommended_action or insight.get("recommended_action")
        timestamp = timestamp or insight.get("timestamp")
    else:
        explanation = insight or ""

    # ── Header ───────────────────────────────────
    icon_name = _SEVERITY_ICONS.get(severity, "mdi:information-outline")
    icon_color = _SEVERITY_COLORS.get(severity, ACCENT_BLUE)

    header_children: list = [
        DashIconify(icon=icon_name, width=16, color=icon_color),
        html.Span(category.upper(), className=f"insight-category {category}"),
    ]

    if timestamp:
        if isinstance(timestamp, str):
            try:
                ts_dt = datetime.fromisoformat(timestamp)
                ts_str = ts_dt.strftime("%H:%M · %d %b")
            except ValueError:
                ts_str = timestamp
        else:
            ts_str = timestamp.strftime("%H:%M · %d %b")
        header_children.append(html.Span(ts_str, className="insight-timestamp"))

    # Zone badges
    zones_to_show = affected_zones or ([zone_id] if zone_id else [])
    for zid in zones_to_show:
        if not zid:
            continue
        zone_info = get_zone_by_id(zid)
        label = zone_info.name if zone_info else zid
        # Shorten long names
        if len(label) > 18:
            label = label[:16] + "…"
        header_children.append(html.Span(label, className="insight-zone-badge"))

    header = html.Div(header_children, className="insight-header")

    # ── Body ─────────────────────────────────────
    body_children: list = []

    if title:
        body_children.append(html.Div(title, className="insight-title"))

    body_children.append(html.Div(explanation, className="insight-body"))

    # ── Action ───────────────────────────────────
    if recommended_action:
        body_children.append(
            html.Div(
                [
                    DashIconify(
                        icon="mdi:lightbulb-on-outline",
                        width=14,
                        color=TEXT_TERTIARY,
                    ),
                    html.Span(recommended_action),
                ],
                className="insight-action",
            )
        )

    # ── Card ─────────────────────────────────────
    severity_class = severity if severity in ("warning", "critical") else ""
    card_class = f"insight-card {severity_class}".strip()

    return html.Div(
        [header, *body_children],
        className=card_class,
    )
