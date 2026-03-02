"""Building status header bar.

Displays building name, overall status indicator, current time,
and quick-action buttons. Sits at the top of the content area.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import TEXT_SECONDARY


def create_header(
    building_name: str = "Centro de Formação Técnica",
) -> html.Div:
    """Create the header status bar component.

    Args:
        building_name: Name to display in the header.

    Returns:
        Dash html.Div containing the header layout.
    """
    left = html.Div(
        [
            html.H1(
                id="header-title",
                children="Overview",
                className="header-title",
            ),
        ],
        className="header-left",
    )

    right = html.Div(
        [
            html.Span(
                id="header-clock",
                children="--:--",
                className="header-clock",
            ),
            html.Span(
                id="header-shift",
                children="—",
                className="header-shift",
            ),
            html.Span(
                [
                    html.Span(className="status-dot healthy"),
                    html.Span("Operational"),
                ],
                id="header-status",
                className="status-badge healthy",
            ),
            html.Span(
                [
                    DashIconify(
                        icon="mdi:bell-outline",
                        width=18,
                        color=TEXT_SECONDARY,
                    ),
                    html.Span(
                        id="header-alert-count",
                        children="0",
                        className="header-alert-badge",
                    ),
                ],
                className="header-alert-count",
            ),
        ],
        className="header-right",
    )

    return html.Div(
        id="header",
        className="header",
        children=[left, right],
    )
