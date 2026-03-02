"""Dash callback registrations.

All callbacks are registered as functions that receive the Dash app
instance and bind Input/Output/State decorators. Callbacks are
organized by page/feature and imported here for centralized registration.
"""

from __future__ import annotations


def register_callbacks(app: object) -> None:
    """Register all dashboard callbacks with the Dash app.

    Args:
        app: The Dash application instance.
    """
    # Callbacks will be registered here as they are implemented:
    # - Navigation callbacks (URL routing)
    # - Data refresh callbacks
    # - Floorplan interaction callbacks
    # - Zone panel callbacks
    # - Chart update callbacks
    pass
