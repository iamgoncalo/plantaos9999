"""Zone detail overlay panel.

Renders a slide-in panel showing detailed metrics, charts, and
status for a selected building zone. Appears on the right side.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.building import get_zone_by_id
from config.theme import TEXT_SECONDARY, TEXT_TERTIARY


def create_zone_panel(zone_id: str | None = None) -> html.Div:
    """Create the zone detail overlay panel.

    Args:
        zone_id: Zone to display details for. None hides the panel.

    Returns:
        Dash html.Div with zone detail layout.
    """
    if zone_id is None:
        return html.Div(
            id="zone-panel",
            className="zone-panel zone-panel-hidden",
        )

    zone = get_zone_by_id(zone_id)
    if zone is None:
        return html.Div(
            id="zone-panel",
            className="zone-panel zone-panel-hidden",
        )

    close_btn = html.Button(
        DashIconify(icon="mdi:close", width=18),
        className="zone-panel-close",
        id="zone-panel-close",
    )

    header = html.Div(
        [
            html.H2(
                zone.name,
                style={"fontSize": "17px", "fontWeight": 600, "margin": 0},
            ),
            html.Div(
                [
                    html.Span(
                        zone.zone_type.value.replace("_", " ").title(),
                        style={
                            "fontSize": "13px",
                            "color": TEXT_SECONDARY,
                        },
                    ),
                    html.Span(" · "),
                    html.Span(
                        f"{zone.area_m2:.0f} m²",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_TERTIARY,
                        },
                    ),
                    html.Span(" · ") if zone.capacity else None,
                    html.Span(
                        f"Cap. {zone.capacity}",
                        style={
                            "fontSize": "13px",
                            "color": TEXT_TERTIARY,
                        },
                    ) if zone.capacity else None,
                ],
                style={"marginTop": "4px"},
            ),
        ],
        className="zone-panel-header",
    )

    metrics_placeholder = html.Div(
        id="zone-panel-metrics",
        children=[
            html.Div(
                "Select a zone to view detailed metrics",
                className="empty-state",
            ),
        ],
        style={"marginTop": "24px"},
    )

    return html.Div(
        id="zone-panel",
        className="zone-panel",
        children=[close_btn, header, metrics_placeholder],
    )
