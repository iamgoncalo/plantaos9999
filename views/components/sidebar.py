"""Left navigation sidebar with icons.

Renders the fixed sidebar with navigation links, building name,
and status indicators. Uses dash-iconify for Material icons.
"""

from __future__ import annotations

from dash import html


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
    return html.Div(
        id="sidebar",
        className="sidebar",
        children=[
            html.Div("PlantaOS", className="sidebar-brand"),
        ],
    )
