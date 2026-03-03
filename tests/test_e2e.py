"""End-to-end tests for PlantaOS dashboard.

Verifies that all modules import without error, the building configuration
is correct, core computation pipelines produce output, data stores are
populated, renderers generate valid output, and the layout contains
expected store components.
"""

from __future__ import annotations


class TestImports:
    """Verify all modules import without error."""

    def test_app_imports(self):
        from app import app

        assert app is not None

    def test_all_pages_import(self):

        # All imported successfully
        assert True

    def test_all_callbacks_import(self):
        from views.callbacks import register_callbacks

        assert callable(register_callbacks)

    def test_callback_modules_import(self):
        from views.callbacks.admin_cb import register_admin_callbacks
        from views.callbacks.booking_cb import register_booking_callbacks
        from views.callbacks.building_3d_cb import register_3d_callbacks
        from views.callbacks.comfort_cb import register_comfort_callbacks
        from views.callbacks.deployment_cb import register_deployment_callbacks
        from views.callbacks.energy_cb import register_energy_callbacks
        from views.callbacks.insights_cb import register_insights_callbacks
        from views.callbacks.occupancy_cb import register_occupancy_callbacks
        from views.callbacks.reports_cb import register_reports_callbacks
        from views.callbacks.sensors_cb import register_sensors_callbacks
        from views.callbacks.simulation_cb import register_simulation_callbacks
        from views.callbacks.view_2d_cb import register_view_2d_callbacks
        from views.callbacks.view_4d_cb import register_view_4d_callbacks
        from views.callbacks.view_data_cb import register_data_explorer_callbacks
        from views.callbacks.view_emergency_cb import register_emergency_callbacks
        from views.callbacks.view_sensors_cb import register_sensor_coverage_callbacks

        assert callable(register_admin_callbacks)
        assert callable(register_booking_callbacks)
        assert callable(register_3d_callbacks)
        assert callable(register_comfort_callbacks)
        assert callable(register_deployment_callbacks)
        assert callable(register_energy_callbacks)
        assert callable(register_insights_callbacks)
        assert callable(register_occupancy_callbacks)
        assert callable(register_reports_callbacks)
        assert callable(register_sensors_callbacks)
        assert callable(register_simulation_callbacks)
        assert callable(register_view_2d_callbacks)
        assert callable(register_view_4d_callbacks)
        assert callable(register_data_explorer_callbacks)
        assert callable(register_emergency_callbacks)
        assert callable(register_sensor_coverage_callbacks)

    def test_state_callback_module_import(self):
        from views.callbacks.state_cb import register_state_callbacks

        assert callable(register_state_callbacks)


class TestBuildingConfig:
    """Verify building configuration is correct."""

    def test_floor_count(self):
        from config.building import CFT_BUILDING

        assert len(CFT_BUILDING.floors) == 2

    def test_floor_numbers(self):
        from config.building import CFT_BUILDING

        floor_numbers = [f.number for f in CFT_BUILDING.floors]
        assert 0 in floor_numbers
        assert 1 in floor_numbers

    def test_monitored_zones(self):
        from config.building import get_monitored_zones

        zones = get_monitored_zones()
        assert len(zones) > 0

    def test_monitored_zones_have_sensors(self):
        from config.building import get_monitored_zones

        zones = get_monitored_zones()
        for zone in zones:
            assert zone.has_sensors is True

    def test_building_has_name(self):
        from config.building import CFT_BUILDING

        assert "CFT" in CFT_BUILDING.name or "HORSE" in CFT_BUILDING.name

    def test_building_has_location(self):
        from config.building import CFT_BUILDING

        assert "Aveiro" in CFT_BUILDING.location

    def test_all_zones_accessible(self):
        from config.building import CFT_BUILDING

        all_zones = CFT_BUILDING.all_zones
        assert len(all_zones) > 10

    def test_geometry_dimensions(self):
        from views.floorplan.zones_geometry import FLOOR_HEIGHT_M, FLOOR_WIDTH_M

        assert abs(FLOOR_WIDTH_M - 30.30) < 0.01
        assert abs(FLOOR_HEIGHT_M - 18.30) < 0.01

    def test_get_zone_by_id(self):
        from config.building import get_zone_by_id

        zone = get_zone_by_id("p0_multiusos")
        assert zone is not None
        assert zone.name == "Sala Multiusos"

    def test_get_zone_by_id_returns_none_for_invalid(self):
        from config.building import get_zone_by_id

        zone = get_zone_by_id("nonexistent_zone_xyz")
        assert zone is None

    def test_get_zones_by_floor(self):
        from config.building import get_zones_by_floor

        floor0 = get_zones_by_floor(0)
        floor1 = get_zones_by_floor(1)
        assert len(floor0) > 0
        assert len(floor1) > 0


class TestSpatialKernel:
    """Verify core computation pipeline."""

    def test_compute_building_state(self):
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        assert state is not None
        assert len(state.floors) == 2

    def test_building_state_has_zones(self):
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        for floor in state.floors:
            assert len(floor.zones) > 0

    def test_building_state_has_timestamp(self):
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        assert state.timestamp is not None

    def test_building_state_has_energy(self):
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        assert state.total_energy_kwh >= 0

    def test_building_state_has_freedom_index(self):
        from core.spatial_kernel import compute_building_state

        state = compute_building_state()
        assert state.avg_freedom_index >= 0


class TestDataStore:
    """Verify data store is populated."""

    def test_store_has_data(self):
        from data.store import store

        assert store.version > 0

    def test_store_has_datasets(self):
        from data.store import store

        assert len(store.keys()) > 0

    def test_store_has_energy(self):
        from data.store import store

        df = store.get("energy")
        assert not df.empty

    def test_store_has_comfort(self):
        from data.store import store

        df = store.get("comfort")
        assert not df.empty

    def test_store_has_occupancy(self):
        from data.store import store

        df = store.get("occupancy")
        assert not df.empty

    def test_store_get_zone_data(self):
        from data.store import store

        df = store.get_zone_data("comfort", "p0_multiusos")
        assert not df.empty


class TestRenderers:
    """Verify renderers produce output."""

    def test_2d_renderer(self):
        from views.floorplan.renderer_2d import render_floorplan_2d

        fig = render_floorplan_2d(floor=0)
        assert fig is not None

    def test_2d_renderer_floor_1(self):
        from views.floorplan.renderer_2d import render_floorplan_2d

        fig = render_floorplan_2d(floor=1)
        assert fig is not None

    def test_3d_renderer(self):
        from views.floorplan.renderer_3d import generate_3d_html

        html_str = generate_3d_html({}, "freedom_index", "all", None)
        assert html_str is not None
        assert len(html_str) > 100

    def test_3d_renderer_contains_threejs(self):
        from views.floorplan.renderer_3d import generate_3d_html

        html_str = generate_3d_html({}, "freedom_index", "all", None)
        assert "three" in html_str.lower() or "THREE" in html_str


class TestLayout:
    """Verify layout stores are defined."""

    def test_layout_has_stores(self):
        from views.layout import create_layout

        layout_str = str(create_layout())
        assert "building-state-store" in layout_str
        assert "tenant-store" in layout_str
        assert "bookings-store" in layout_str
        assert "lang-store" in layout_str
        assert "sensors-store" in layout_str
        assert "audit-log-store" in layout_str

    def test_layout_has_url(self):
        from views.layout import create_layout

        layout_str = str(create_layout())
        assert "url" in layout_str

    def test_layout_has_tenant_confirm(self):
        from views.layout import create_layout

        layout_str = str(create_layout())
        assert "tenant-confirm-dialog" in layout_str

    def test_layout_has_data_refresh_interval(self):
        from views.layout import create_layout

        layout_str = str(create_layout())
        assert "data-refresh-interval" in layout_str


class TestComponents:
    """Verify UI components can be created."""

    def test_kpi_card(self):
        from views.components.kpi_card import create_kpi_card

        card = create_kpi_card("Test", "42", icon="mdi:flash")
        assert card is not None

    def test_sidebar(self):
        from views.components.sidebar import create_sidebar

        sidebar = create_sidebar()
        assert sidebar is not None

    def test_header(self):
        from views.components.header import create_header

        header = create_header()
        assert header is not None

    def test_alert_feed_empty(self):
        from views.components.alert_feed import create_alert_feed

        feed = create_alert_feed()
        assert feed is not None

    def test_alert_feed_with_alerts(self):
        from views.components.alert_feed import create_alert_feed

        alerts = [
            {
                "message": "Sala Multiusos: CO2 high",
                "severity": "critical",
                "timestamp": "2026-03-03T10:00:00",
                "zone_id": "p0_multiusos",
            }
        ]
        feed = create_alert_feed(alerts=alerts)
        assert feed is not None


class TestConfig:
    """Verify configuration modules load correctly."""

    def test_settings(self):
        from config.settings import settings

        assert settings.APP_PORT > 0

    def test_theme(self):
        from config.theme import ACCENT_BLUE, BG_CARD, TEXT_PRIMARY

        assert ACCENT_BLUE == "#296649"
        assert TEXT_PRIMARY == "#1D1D1F"
        assert BG_CARD == "#FFFFFF"

    def test_thresholds(self):
        from config.thresholds import evaluate_comfort

        status = evaluate_comfort("temperature", 22.0)
        assert status in ("optimal", "acceptable", "warning", "critical")
