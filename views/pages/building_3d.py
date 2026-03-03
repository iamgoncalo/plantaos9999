"""3D building view page.

Wraps the Three.js 3D renderer in an html.Iframe component with
controls for metric selection, floor filtering, and camera position.
"""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import TEXT_TERTIARY


def create_building_3d_page() -> html.Div:
    """Create the 3D building view page layout.

    Returns:
        Dash html.Div containing the 3D view iframe and
        metric/floor controls.
    """
    viewer_placeholder = html.Div(
        [
            DashIconify(
                icon="mdi:cube-outline",
                width=48,
                color=TEXT_TERTIARY,
            ),
            html.Div(
                "3D Building View",
                style={
                    "marginTop": "12px",
                    "fontSize": "17px",
                    "fontWeight": 600,
                    "color": TEXT_TERTIARY,
                },
            ),
            html.Div(
                "Three.js interactive model will be rendered here",
                style={
                    "marginTop": "8px",
                    "fontSize": "14px",
                    "color": TEXT_TERTIARY,
                },
            ),
        ],
        className="card",
        style={
            "minHeight": "500px",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
        },
        id="building-3d-viewer",
    )

    return html.Div(
        [viewer_placeholder],
        className="page-enter",
    )
