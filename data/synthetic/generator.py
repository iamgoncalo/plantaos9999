"""Master synthetic data generator.

Orchestrates all profile generators (energy, comfort, occupancy, events)
to produce a coherent set of time-series data for the CFT building.
Generates 30 days of history at configurable intervals.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger


def generate_all(days: int = 30, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Generate all synthetic datasets.

    Coordinates energy, comfort, occupancy, and event generators to
    produce temporally consistent data across all zones.

    Args:
        days: Number of days of history to generate.
        seed: Random seed for reproducibility.

    Returns:
        Dict mapping dataset names to DataFrames:
        'energy', 'comfort', 'occupancy', 'weather', 'schedule'.
    """
    ...


def _create_time_index(
    days: int,
    interval_minutes: int = 15,
) -> pd.DatetimeIndex:
    """Create a DatetimeIndex spanning the given number of days.

    Args:
        days: Number of days to cover.
        interval_minutes: Time resolution in minutes.

    Returns:
        DatetimeIndex from (now - days) to now.
    """
    ...


if __name__ == "__main__":
    logger.info("Generating synthetic data...")
    datasets = generate_all()
    for name, df in datasets.items():
        logger.info(f"  {name}: {len(df)} rows")
    logger.info("Done.")
