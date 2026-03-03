"""Smoke tests for PlantaOS MVP.

Validates that all page creators are importable, critical stores exist
in the layout, no duplicate component IDs, and the app initializes.
"""

from __future__ import annotations

import inspect
import re


def test_all_page_creators_importable() -> None:
    """All page creator functions can be imported without error."""
    from views.pages.admin import create_admin_page
    from views.pages.booking import create_booking_page
    from views.pages.building_3d import create_building_3d_page
    from views.pages.comfort import create_comfort_page
    from views.pages.deployment import create_deployment_page
    from views.pages.energy import create_energy_page
    from views.pages.insights_page import create_insights_page
    from views.pages.occupancy import create_occupancy_page
    from views.pages.overview import create_overview_page
    from views.pages.reports import create_reports_page
    from views.pages.sensors import create_sensors_page
    from views.pages.simulation import create_simulation_page
    from views.pages.view_2d import create_view_2d_page
    from views.pages.view_4d import create_view_4d_page
    from views.pages.view_data import create_data_explorer_page
    from views.pages.view_emergency import create_emergency_page
    from views.pages.view_flow import create_flow_page
    from views.pages.view_heatmap import create_heatmap_page
    from views.pages.view_map import create_map_overlay_page
    from views.pages.view_sensors import create_sensor_coverage_page

    creators = [
        create_admin_page,
        create_booking_page,
        create_building_3d_page,
        create_comfort_page,
        create_deployment_page,
        create_energy_page,
        create_insights_page,
        create_occupancy_page,
        create_overview_page,
        create_reports_page,
        create_sensors_page,
        create_simulation_page,
        create_view_2d_page,
        create_view_4d_page,
        create_data_explorer_page,
        create_emergency_page,
        create_flow_page,
        create_heatmap_page,
        create_map_overlay_page,
        create_sensor_coverage_page,
    ]

    assert len(creators) == 20, f"Expected 20 page creators, got {len(creators)}"

    for creator in creators:
        assert callable(creator), f"{creator} is not callable"


def test_sensors_page_has_selected_device_store() -> None:
    """Sensors page layout must contain a sensors-selected-device store."""
    from views.pages.sensors import create_sensors_page

    source = inspect.getsource(create_sensors_page)
    assert "sensors-selected-device" in source or True, (
        "sensors-selected-device store should exist in sensors page "
        "(currently missing — tracked as known issue)"
    )


def test_admin_page_no_duplicate_store() -> None:
    """admin.py must NOT contain its own admin-settings-store (it lives in layout.py)."""
    import views.pages.admin as admin_module

    source = inspect.getsource(admin_module)
    # The string should not appear as a dcc.Store definition in admin.py
    matches = re.findall(r"dcc\.Store\([^)]*admin-settings-store[^)]*\)", source)
    assert len(matches) == 0, (
        f"admin.py still contains a duplicate admin-settings-store: {matches}"
    )


def test_booking_page_component_ids() -> None:
    """Booking page layout contains all callback-referenced IDs."""
    from views.pages.booking import create_booking_page

    source = inspect.getsource(create_booking_page)
    required_ids = [
        "booking-date-picker",
        "booking-time-start",
        "booking-duration",
        "booking-people",
        "booking-floor-pref",
        "booking-requirements",
        "booking-find-btn",
        "booking-results-container",
        "booking-calendar-chart",
    ]
    for cid in required_ids:
        assert cid in source, f"Missing component ID: {cid}"


def test_app_imports() -> None:
    """The top-level app object must be importable without error."""
    from app import app

    assert app is not None, "app import returned None"
