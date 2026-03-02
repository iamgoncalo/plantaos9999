"""Comfort page: thermal and air quality heatmaps.

Displays temperature, humidity, CO2, and illuminance across zones
as heatmaps with threshold indicators and trend charts.
"""

from __future__ import annotations

from dash import html


def create_comfort_page() -> html.Div:
    """Create the comfort monitoring page layout.

    Returns:
        Dash html.Div containing the comfort page with zone
        heatmaps and metric trend charts.
    """
    ...
