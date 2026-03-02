"""Building status header bar.

Displays building name, overall status indicator, current time,
and quick-action buttons. Sits at the top of the content area.
"""

from __future__ import annotations

from dash import html


def create_header(
    building_name: str = "Centro de Formação Técnica",
) -> html.Div:
    """Create the header status bar component.

    Args:
        building_name: Name to display in the header.

    Returns:
        Dash html.Div containing the header layout.
    """
    return html.Div(
        id="header",
        className="header",
        children=[
            html.H1(building_name, style={"fontSize": "17px", "fontWeight": 600}),
        ],
    )
