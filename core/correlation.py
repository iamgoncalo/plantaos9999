"""Cross-metric correlation analysis.

Computes correlations between energy↔occupancy, comfort↔weather,
and other metric pairs. Identifies significant relationships
for insight generation.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger
from pydantic import BaseModel
from scipy import stats

from config.building import get_monitored_zones
from data.store import store


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
    energy_df = store.get("energy")
    occ_df = store.get("occupancy")

    if energy_df is None or occ_df is None:
        return _empty_result("total_kwh", "occupant_count")

    if zone_id:
        energy_df = energy_df[energy_df["zone_id"] == zone_id]
        occ_df = occ_df[occ_df["zone_id"] == zone_id]

    if energy_df.empty or occ_df.empty:
        return _empty_result("total_kwh", "occupant_count")

    # Aggregate to 15-min resolution and align
    energy_ts = energy_df.groupby(pd.Grouper(key="timestamp", freq="15min"))[
        "total_kwh"
    ].sum()
    occ_ts = occ_df.groupby(pd.Grouper(key="timestamp", freq="15min"))[
        "occupant_count"
    ].sum()

    # Align on common timestamps
    aligned = pd.DataFrame({"energy": energy_ts, "occupancy": occ_ts}).dropna()
    if len(aligned) < 10:
        return _empty_result("total_kwh", "occupant_count")

    coeff, p_val = _compute_pearson(aligned["energy"], aligned["occupancy"])

    interpretation = _interpret_correlation(coeff, "energy", "occupancy")

    return CorrelationResult(
        metric_a="total_kwh",
        metric_b="occupant_count",
        coefficient=round(coeff, 4),
        p_value=round(p_val, 6),
        n_samples=len(aligned),
        is_significant=p_val < 0.05,
        interpretation=interpretation,
    )


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
    comfort_col_map = {
        "temperature": ("temperature_c", "outdoor_temp_c"),
        "humidity": ("humidity_pct", "outdoor_humidity_pct"),
    }

    if metric not in comfort_col_map:
        return _empty_result(f"indoor_{metric}", f"outdoor_{metric}")

    indoor_col, outdoor_col = comfort_col_map[metric]

    comfort_df = store.get("comfort")
    weather_df = store.get("weather")

    if comfort_df is None or weather_df is None:
        return _empty_result(indoor_col, outdoor_col)

    if zone_id:
        comfort_df = comfort_df[comfort_df["zone_id"] == zone_id]

    if comfort_df.empty or weather_df.empty:
        return _empty_result(indoor_col, outdoor_col)

    # Aggregate comfort to 15-min resolution
    indoor_ts = comfort_df.groupby(pd.Grouper(key="timestamp", freq="15min"))[
        indoor_col
    ].mean()
    outdoor_ts = weather_df.set_index("timestamp")[outdoor_col]

    aligned = pd.DataFrame({"indoor": indoor_ts, "outdoor": outdoor_ts}).dropna()
    if len(aligned) < 10:
        return _empty_result(indoor_col, outdoor_col)

    coeff, p_val = _compute_pearson(aligned["indoor"], aligned["outdoor"])

    interpretation = _interpret_correlation(
        coeff, f"indoor {metric}", f"outdoor {metric}"
    )

    return CorrelationResult(
        metric_a=indoor_col,
        metric_b=outdoor_col,
        coefficient=round(coeff, 4),
        p_value=round(p_val, 6),
        n_samples=len(aligned),
        is_significant=p_val < 0.05,
        interpretation=interpretation,
    )


def compute_all_correlations() -> dict[str, CorrelationResult]:
    """Compute all standard correlation pairs for the building.

    Returns:
        Dict mapping correlation pair names to results.
    """
    results: dict[str, CorrelationResult] = {}

    # Building-wide correlations
    results["building_energy_occupancy"] = energy_occupancy_correlation()
    results["building_temp_weather"] = comfort_weather_correlation(metric="temperature")
    results["building_humidity_weather"] = comfort_weather_correlation(
        metric="humidity"
    )

    # Per-zone correlations for monitored zones
    monitored = get_monitored_zones()
    for zone in monitored:
        zid = zone.id
        results[f"{zid}_energy_occupancy"] = energy_occupancy_correlation(zid)
        results[f"{zid}_temp_weather"] = comfort_weather_correlation(zid, "temperature")

    logger.info(f"Computed {len(results)} correlations")
    return results


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
    # Drop any remaining NaN
    mask = series_a.notna() & series_b.notna()
    a = series_a[mask]
    b = series_b[mask]

    if len(a) < 3:
        return 0.0, 1.0

    # Check for constant series
    if a.std() < 1e-10 or b.std() < 1e-10:
        return 0.0, 1.0

    coeff, p_val = stats.pearsonr(a, b)
    return float(coeff), float(p_val)


def _interpret_correlation(coeff: float, name_a: str, name_b: str) -> str:
    """Generate human-readable interpretation of a correlation.

    Args:
        coeff: Pearson correlation coefficient.
        name_a: Name of first variable.
        name_b: Name of second variable.

    Returns:
        Interpretation string.
    """
    abs_coeff = abs(coeff)
    direction = "positive" if coeff > 0 else "negative"

    if abs_coeff >= 0.8:
        strength = "very strong"
    elif abs_coeff >= 0.6:
        strength = "strong"
    elif abs_coeff >= 0.4:
        strength = "moderate"
    elif abs_coeff >= 0.2:
        strength = "weak"
    else:
        return f"No meaningful correlation between {name_a} and {name_b}"

    return f"{strength.capitalize()} {direction} correlation (r={coeff:.2f}) between {name_a} and {name_b}"


def _empty_result(metric_a: str, metric_b: str) -> CorrelationResult:
    """Create an empty correlation result.

    Args:
        metric_a: First metric name.
        metric_b: Second metric name.

    Returns:
        CorrelationResult with zero values.
    """
    return CorrelationResult(
        metric_a=metric_a,
        metric_b=metric_b,
        coefficient=0.0,
        p_value=1.0,
        n_samples=0,
        is_significant=False,
        interpretation="Insufficient data for correlation analysis",
    )
