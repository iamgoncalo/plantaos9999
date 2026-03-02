"""Left navigation sidebar with icons.

Renders the fixed sidebar with navigation links, building name,
and status indicators. Uses dash-iconify for Material icons.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    FONT_SIZE_XL,
    FONT_SIZE_XS,
    SPACING_SM,
    STATUS_HEALTHY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WEIGHT_SEMIBOLD,
)


# Navigation items: id, label, icon (dash-iconify format)
NAV_ITEMS: list[dict[str, str]] = [
    {"id": "overview", "label": "Overview", "icon": "mdi:view-dashboard"},
    {"id": "energy", "label": "Energy", "icon": "mdi:flash"},
    {"id": "comfort", "label": "Comfort", "icon": "mdi:thermometer"},
    {"id": "occupancy", "label": "Occupancy", "icon": "mdi:account-group"},
    {"id": "insights", "label": "Insights", "icon": "mdi:lightbulb-on"},
    {"id": "building_3d", "label": "3D View", "icon": "mdi:cube-outline"},
]


def create_sidebar(active_page: str = "overview") -> html.Div:
    """Create the sidebar navigation component.

    Args:
        active_page: Currently active page ID for highlighting.

    Returns:
        Dash html.Div containing the sidebar layout.
    """
    brand = html.Div(
        [
            html.Div("PlantaOS", className="sidebar-brand"),
            html.Div("Digital Twin", className="sidebar-brand-subtitle"),
        ],
        style={"marginBottom": f"{SPACING_SM}px"},
    )

    nav_items = []
    for item in NAV_ITEMS:
        href = "/" if item["id"] == "overview" else f"/{item['id']}"
        is_active = item["id"] == active_page
        class_name = "sidebar-nav-item active" if is_active else "sidebar-nav-item"

        nav_link = dcc.Link(
            html.Div(
                [
                    DashIconify(
                        icon=item["icon"],
                        width=20,
                        color=ACCENT_BLUE if is_active else TEXT_SECONDARY,
                    ),
                    html.Span(item["label"]),
                ],
                className=class_name,
                id=f"nav-{item['id']}",
            ),
            href=href,
        )
        nav_items.append(nav_link)

    nav = html.Nav(
        nav_items,
        style={"display": "flex", "flexDirection": "column", "gap": "4px"},
    )

    health_indicator = html.Div(
        [
            html.Div(
                [
                    html.Span(className="status-dot healthy"),
                    html.Span(
                        "Building Health",
                        style={
                            "fontSize": FONT_SIZE_XS,
                            "fontWeight": WEIGHT_SEMIBOLD,
                            "color": TEXT_SECONDARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginBottom": "4px",
                },
            ),
            html.Div(
                id="sidebar-health-score",
                children=[
                    html.Span(
                        "—",
                        style={
                            "fontSize": FONT_SIZE_XL,
                            "fontWeight": WEIGHT_SEMIBOLD,
                            "color": STATUS_HEALTHY,
                        },
                    ),
                    html.Span(
                        " / 100",
                        style={
                            "fontSize": FONT_SIZE_XS,
                            "color": TEXT_TERTIARY,
                        },
                    ),
                ],
            ),
        ],
        className="sidebar-bottom",
    )

    return html.Div(
        id="sidebar",
        className="sidebar",
        children=[brand, nav, health_indicator],
    )
