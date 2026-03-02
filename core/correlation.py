"""Cross-metric correlation analysis.

Computes correlations between energy↔occupancy, comfort↔weather,
and other metric pairs. Identifies significant relationships
for insight generation.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel


class CorrelationResult(BaseModel):
    """Result of a correlation computation."""

    metric_a: str
    metric_b: str
    coefficient: float
    p_value: float
    n_samples: int
    is_significant: bool
    interpretation: str = ""


def energy_occupancy_correlation(
    zone_id: str | None = None,
) -> CorrelationResult:
    """Compute correlation between energy usage and occupancy.

    Args:
        zone_id: Optional zone filter. None = building-wide.

    Returns:
        CorrelationResult with Pearson coefficient and interpretation.
    """
    ...


def comfort_weather_correlation(
    zone_id: str | None = None,
    metric: str = "temperature",
) -> CorrelationResult:
    """Compute correlation between indoor comfort and outdoor weather.

    Args:
        zone_id: Optional zone filter.
        metric: Comfort metric to correlate (e.g., 'temperature', 'humidity').

    Returns:
        CorrelationResult with coefficient and interpretation.
    """
    ...


def compute_all_correlations() -> dict[str, CorrelationResult]:
    """Compute all standard correlation pairs for the building.

    Returns:
        Dict mapping correlation pair names to results.
    """
    ...


def _compute_pearson(
    series_a: pd.Series,
    series_b: pd.Series,
) -> tuple[float, float]:
    """Compute Pearson correlation coefficient and p-value.

    Args:
        series_a: First time series.
        series_b: Second time series.

    Returns:
        Tuple of (coefficient, p_value).
    """
    ...
