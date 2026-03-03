"""Static callback-ID integrity checks."""

from __future__ import annotations

import inspect
import re


# IDs that are known to be dynamic (pattern matching, generated at runtime)
_DYNAMIC_IDS = {
    "sensor-row",
    "zone-overlay",
    "zone-label",
}

# Global stores and components from layout.py
_GLOBAL_IDS = {
    "url",
    "building-state-store",
    "sidebar-open-store",
    "tenant-store",
    "admin-settings-store",
    "bookings-store",
    "lang-store",
    "sensors-store",
    "audit-log-store",
    "notifications-store",
    "active-floor-store",
    "auth-store",
    "notification-open-store",
    "tenant-pending-store",
    "sensors-selected-device",
    "sensors-action-store",
    "tenant-confirm-dialog",
    "data-refresh-interval",
    "sidebar-overlay",
    "page-content",
    "main-content-area",
}


def _extract_callback_ids(source: str) -> set[str]:
    """Extract component IDs from Input/Output/State declarations."""
    pattern = re.compile(r'(?:Input|Output|State)\(\s*["\']([a-z][\w-]*)["\']')
    return set(pattern.findall(source))


def test_layout_has_all_global_stores() -> None:
    """layout.py must define all expected global stores."""
    from views.layout import create_layout

    layout_str = str(create_layout())
    for store_id in _GLOBAL_IDS:
        assert store_id in layout_str, f"Global ID '{store_id}' missing from layout"


def test_callback_ids_exist_in_layout_or_pages() -> None:
    """All callback Input/Output/State IDs must exist in layout or pages."""
    from views.layout import create_layout

    layout_str = str(create_layout())

    # Collect page IDs from all page creators
    page_sources: list[str] = []
    page_modules = [
        "views.pages.overview",
        "views.pages.energy",
        "views.pages.comfort",
        "views.pages.occupancy",
        "views.pages.insights_page",
        "views.pages.building_3d",
        "views.pages.simulation",
        "views.pages.reports",
        "views.pages.booking",
        "views.pages.admin",
        "views.pages.view_2d",
        "views.pages.view_4d",
        "views.pages.view_context",
        "views.pages.view_data",
        "views.pages.view_emergency",
        "views.pages.view_sensors",
        "views.pages.deployment",
    ]
    for mod_name in page_modules:
        try:
            mod = __import__(mod_name, fromlist=["create"])
            for name in dir(mod):
                fn = getattr(mod, name)
                if callable(fn) and name.startswith("create_"):
                    page_sources.append(inspect.getsource(fn))
        except (ImportError, AttributeError):
            continue

    all_page_text = " ".join(page_sources)

    # Now check a subset of critical callback files
    import views.callbacks.state_cb as state_cb
    import views.callbacks.nav_cb as nav_cb

    for cb_mod in [state_cb, nav_cb]:
        source = inspect.getsource(cb_mod)
        ids = _extract_callback_ids(source)
        for cid in ids:
            if cid in _DYNAMIC_IDS:
                continue
            in_layout = cid in layout_str
            in_pages = cid in all_page_text
            assert in_layout or in_pages, (
                f"Callback ID '{cid}' from {cb_mod.__name__} not found "
                "in layout or any page creator"
            )
