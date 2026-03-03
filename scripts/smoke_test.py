"""Smoke test -- imports app, runs key functions, asserts no exceptions."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_PASS = 0
_FAIL = 0


def _run_test(name: str, fn: object) -> bool:
    """Run a single test function and report result.

    Args:
        name: Human-readable test name.
        fn: Callable to execute.

    Returns:
        True if test passed, False otherwise.
    """
    global _PASS, _FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        _PASS += 1
        return True
    except Exception as exc:
        print(f"  [FAIL] {name}: {exc}")
        traceback.print_exc()
        _FAIL += 1
        return False


def test_import_app() -> None:
    """Verify that the Dash app can be imported without error."""
    from app import app  # noqa: F401

    assert app is not None, "app object is None"


def test_import_building_config() -> None:
    """Verify building config loads zones successfully."""
    from config.building import get_monitored_zones

    zones = get_monitored_zones()
    assert len(zones) > 0, "No monitored zones found"


def test_compute_building_state() -> None:
    """Verify compute_building_state runs and returns data."""
    from core.spatial_kernel import compute_building_state

    state = compute_building_state()
    assert state is not None, "Building state is None"
    data = state.model_dump(mode="json")
    assert "floors" in data, "Missing floors key"


def test_render_floorplan_2d() -> None:
    """Verify 2D floorplan renders without error."""
    from views.floorplan.renderer_2d import render_floorplan_2d

    fig = render_floorplan_2d(floor=0)
    assert fig is not None, "Floorplan figure is None"


def test_data_store_loaded() -> None:
    """Verify the data store has been populated."""
    from data.store import store

    keys = list(store.keys())
    assert len(keys) > 0, "Data store is empty"


def test_theme_constants() -> None:
    """Verify theme config exports expected constants."""
    from config.theme import ACCENT_BLUE, BG_CARD

    assert ACCENT_BLUE is not None, "ACCENT_BLUE missing"
    assert BG_CARD is not None, "BG_CARD missing"


def main() -> int:
    """Run all smoke tests and report summary.

    Returns:
        Exit code: 0 if all pass, 1 if any fail.
    """
    print("PlantaOS Smoke Test Suite")
    print("=" * 40)

    tests = [
        ("Import app module", test_import_app),
        ("Import building config", test_import_building_config),
        ("Compute building state", test_compute_building_state),
        ("Render 2D floorplan", test_render_floorplan_2d),
        ("Data store loaded", test_data_store_loaded),
        ("Theme constants", test_theme_constants),
    ]

    for name, fn in tests:
        _run_test(name, fn)

    print("=" * 40)
    total = _PASS + _FAIL
    print(f"Results: {_PASS}/{total} passed, {_FAIL} failed")

    if _FAIL > 0:
        print("\nSome smoke tests FAILED.")
        return 1

    print("\nAll smoke tests PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
