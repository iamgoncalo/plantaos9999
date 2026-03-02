"""Single KPI display card with trend arrow.

Renders a metric value, label, and trend indicator in the
Apple-inspired card design.
"""

from __future__ import annotations

from dash import html


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
    ...
