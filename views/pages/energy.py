"""Energy page: breakdown, baselines, and anomalies.

Shows energy consumption by zone and category (HVAC 60%, lighting 20%,
equipment 15%, other 5%), baseline comparisons, and detected anomalies.
"""

from __future__ import annotations

from dash import html


def create_energy_page() -> html.Div:
    """Create the energy analysis page layout.

    Returns:
        Dash html.Div containing the energy page with breakdown
        charts, baseline comparison, and anomaly markers.
    """
    ...
