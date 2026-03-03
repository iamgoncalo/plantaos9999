"""Building status header bar with global search.

Displays building name, global search bar, overall status indicator,
current time, and quick-action buttons. Sits at the top of the content area.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import ACCENT_BLUE, TEXT_SECONDARY, TEXT_TERTIARY


def create_header(
    building_name: str = "Centro de Formação Técnica",
) -> html.Div:
    """Create the header status bar component.

    Args:
        building_name: Name to display in the header.

    Returns:
        Dash html.Div containing the header layout.
    """
    # Hamburger button for mobile sidebar toggle (hidden on desktop via CSS)
    hamburger = html.Button(
        DashIconify(icon="mdi:menu", width=24),
        id="sidebar-toggle-btn",
        className="sidebar-toggle-btn",
        n_clicks=0,
    )

    left = html.Div(
        [
            hamburger,
            html.H1(
                id="header-title",
                children="Overview",
                className="header-title",
            ),
        ],
        className="header-left",
    )

    # Global search bar (Gemini-style)
    search_bar = html.Div(
        [
            DashIconify(
                icon="mdi:magnify",
                width=18,
                color=TEXT_TERTIARY,
                style={"flexShrink": 0},
            ),
            dcc.Input(
                id="global-search-input",
                type="text",
                placeholder="Search zones, metrics, insights...",
                debounce=True,
                className="global-search-field",
            ),
        ],
        className="global-search-bar",
    )

    # Tenant badge
    tenant_badge = html.Span(
        [
            DashIconify(
                icon="mdi:domain",
                width=14,
                color=ACCENT_BLUE,
            ),
            html.Span("HORSE Renault"),
        ],
        className="tenant-badge",
    )

    right = html.Div(
        [
            tenant_badge,
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
        children=[left, search_bar, right],
    )
