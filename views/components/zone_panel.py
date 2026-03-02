"""Zone detail overlay panel.

Renders a slide-in panel showing detailed metrics, charts, and
status for a selected building zone. Appears on the right side.
"""

from __future__ import annotations

from dash import html


def create_zone_panel(zone_id: str | None = None) -> html.Div:
    """Create the zone detail overlay panel.

    Args:
        zone_id: Zone to display details for. None hides the panel.

    Returns:
        Dash html.Div with zone detail layout.
    """
    ...
