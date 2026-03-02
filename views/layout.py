"""App shell: sidebar + header + content area.

Defines the top-level layout combining the sidebar navigation,
header status bar, and page content container with URL routing.
"""

from __future__ import annotations

from dash import dcc, html

from views.components.header import create_header
from views.components.sidebar import create_sidebar


def create_layout() -> html.Div:
    """Create the main application layout.

    Returns:
        Dash html.Div containing the complete app shell with
        sidebar, header, and content area with URL routing.
    """
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="building-state-store", storage_type="memory"),
            create_sidebar(),
            html.Div(
                [
                    create_header(),
                    html.Div(id="page-content", className="content"),
                ],
                style={"marginLeft": "240px"},
            ),
        ],
    )
