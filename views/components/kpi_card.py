"""Single KPI display card with trend arrow.

Renders a metric value, label, and trend indicator in the
Apple-inspired card design.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_LIGHT,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    TEXT_TERTIARY,
)


def create_kpi_card(
    title: str,
    value: str,
    trend: float | None = None,
    unit: str = "",
    icon: str | None = None,
) -> html.Div:
    """Create a KPI card component.

    Args:
        title: Metric label (e.g., 'Total Energy').
        value: Formatted value string.
        trend: Percentage change (positive = up, negative = down).
        unit: Unit suffix (e.g., 'kWh').
        icon: Optional dash-iconify icon name.

    Returns:
        Dash html.Div with KPI card layout.
    """
    children: list = []

    if icon:
        children.append(
            html.Div(
                DashIconify(icon=icon, width=22, color=ACCENT_BLUE),
                className="kpi-icon",
                style={"background": ACCENT_BLUE_LIGHT},
            )
        )

    value_row = html.Div(
        [
            html.Span(value, className="kpi-value"),
            html.Span(unit, className="kpi-unit") if unit else None,
        ],
    )
    children.append(value_row)

    children.append(html.Div(title, className="kpi-label"))

    if trend is not None:
        if trend > 0:
            arrow = "▲"
            trend_class = "kpi-trend up"
            color = STATUS_HEALTHY
        elif trend < 0:
            arrow = "▼"
            trend_class = "kpi-trend down"
            color = STATUS_CRITICAL
        else:
            arrow = "—"
            trend_class = "kpi-trend neutral"
            color = TEXT_TERTIARY

        children.append(
            html.Div(
                f"{arrow} {abs(trend):.1f}%",
                className=trend_class,
                style={"color": color},
            )
        )

    return html.Div(className="kpi-card", children=children)


def create_kpi_skeleton() -> html.Div:
    """Create a skeleton placeholder KPI card for loading state.

    Returns:
        Dash html.Div matching KPI card dimensions with skeleton animation.
    """
    return html.Div(
        [
            html.Div(className="skeleton", style={"width": "40px", "height": "40px"}),
            html.Div(
                className="skeleton",
                style={"width": "80px", "height": "28px", "marginTop": "12px"},
            ),
            html.Div(
                className="skeleton",
                style={"width": "100px", "height": "14px", "marginTop": "8px"},
            ),
        ],
        className="kpi-card",
        style={"display": "flex", "flexDirection": "column", "alignItems": "center"},
    )
