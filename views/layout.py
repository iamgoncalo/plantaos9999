"""App shell: sidebar + header + content area.

Defines the top-level layout combining the sidebar navigation,
header status bar, and page content container with URL routing.
"""

from __future__ import annotations

from dash import dcc, html

from config.settings import settings
from views.components.header import create_header
from views.components.sidebar import create_sidebar
from views.components.zone_panel import create_zone_panel

# Demo mode: 5s refresh (minimum allowed). Normal: use setting.
_REFRESH_MS = 5_000 if settings.DEMO_MODE else settings.DATA_REFRESH_INTERVAL * 1000


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
            dcc.Store(id="sidebar-open-store", storage_type="memory", data=False),
            dcc.Store(id="tenant-store", storage_type="local", data="horse_renault"),
            dcc.Store(id="admin-settings-store", storage_type="local"),
            dcc.Store(id="bookings-store", storage_type="memory", data=[]),
            dcc.Store(id="lang-store", storage_type="local", data="en"),
            dcc.Store(id="sensors-store", storage_type="local", data=[]),
            dcc.Store(id="audit-log-store", storage_type="memory", data=[]),
            dcc.Store(id="notification-open-store", storage_type="memory", data=False),
            dcc.Store(id="tenant-pending-store", storage_type="memory"),
            dcc.ConfirmDialog(
                id="tenant-confirm-dialog",
                message=(
                    "Switching tenant will change all building data, reports,"
                    " and sensor configurations. Are you sure?"
                ),
            ),
            dcc.Interval(
                id="data-refresh-interval",
                interval=_REFRESH_MS,
                n_intervals=0,
            ),
            create_sidebar(),
            html.Div(id="sidebar-overlay", className="sidebar-overlay"),
            html.Div(
                [
                    create_header(),
                    html.Div(id="page-content", className="content"),
                ],
                className="main-content",
                id="main-content-area",
            ),
            create_zone_panel(),
        ],
    )
