"""Left navigation sidebar with icons.

Renders the fixed sidebar with navigation links, building name,
and status indicators. Uses dash-iconify for Material icons.
Supports collapsible submenu for View items (2D/3D/4D).
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
# Items with "submenu" key contain child navigation items.
NAV_ITEMS: list[dict] = [
    {"id": "overview", "label": "Overview", "icon": "mdi:view-dashboard"},
    {
        "id": "view",
        "label": "View",
        "icon": "mdi:eye-outline",
        "submenu": [
            {"id": "view_2d", "label": "2D Map", "icon": "mdi:map-outline"},
            {"id": "building_3d", "label": "3D Orbit", "icon": "mdi:cube-outline"},
            {"id": "building_3d_walk", "label": "3D Walk", "icon": "mdi:walk"},
            {"id": "view_4d", "label": "Timeline (4D)", "icon": "mdi:clock-fast"},
            {"id": "view_flow", "label": "Flow", "icon": "mdi:swap-horizontal"},
            {"id": "view_heatmap", "label": "Heatmap", "icon": "mdi:grid"},
        ],
    },
    {"id": "booking", "label": "Booking", "icon": "mdi:calendar-clock"},
    {"id": "simulation", "label": "Simulation", "icon": "mdi:play-circle-outline"},
    {"id": "insights", "label": "Insights", "icon": "mdi:lightbulb-on"},
    {"id": "reports", "label": "Reports", "icon": "mdi:file-chart-outline"},
    {"id": "sensors", "label": "Sensors", "icon": "mdi:access-point"},
    {"id": "admin", "label": "Settings", "icon": "mdi:cog-outline"},
]


def _build_nav_link(
    item: dict,
    active_page: str,
) -> dcc.Link:
    """Build a single nav link element.

    Args:
        item: Nav item dict with id, label, icon.
        active_page: Currently active page ID.

    Returns:
        Dash dcc.Link wrapping the nav item.
    """
    href = "/" if item["id"] == "overview" else f"/{item['id']}"
    is_active = item["id"] == active_page
    class_name = "sidebar-nav-item active" if is_active else "sidebar-nav-item"

    return dcc.Link(
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

    nav_items: list = []
    for item in NAV_ITEMS:
        if "submenu" in item:
            # Check if any submenu item is active
            sub_ids = [sub["id"] for sub in item["submenu"]]
            is_parent_active = active_page in sub_ids
            parent_class = (
                "sidebar-nav-item has-submenu active"
                if is_parent_active
                else "sidebar-nav-item has-submenu"
            )

            parent_el = html.Div(
                [
                    DashIconify(
                        icon=item["icon"],
                        width=20,
                        color=ACCENT_BLUE if is_parent_active else TEXT_SECONDARY,
                    ),
                    html.Span(item["label"]),
                    DashIconify(
                        icon=(
                            "mdi:chevron-down"
                            if is_parent_active
                            else "mdi:chevron-right"
                        ),
                        width=16,
                        color=TEXT_TERTIARY,
                        style={"marginLeft": "auto"},
                    ),
                ],
                className=parent_class,
                id=f"nav-{item['id']}",
            )
            nav_items.append(parent_el)

            # Submenu items (visible when parent is active)
            submenu_style = {
                "display": "flex" if is_parent_active else "none",
                "flexDirection": "column",
                "gap": "2px",
                "paddingLeft": "20px",
            }
            submenu_children = [
                _build_nav_link(sub, active_page) for sub in item["submenu"]
            ]
            nav_items.append(
                html.Div(
                    submenu_children,
                    id="submenu-view",
                    className="sidebar-submenu",
                    style=submenu_style,
                )
            )
        else:
            nav_items.append(_build_nav_link(item, active_page))

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
                        "Zone Performance",
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
