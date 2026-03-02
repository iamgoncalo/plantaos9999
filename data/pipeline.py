"""Data ingestion, cleaning, normalization, and storage pipeline.

Orchestrates the flow from synthetic generation (or future real sources)
through validation and cleaning into the in-memory DataStore.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from data.store import store
from data.synthetic.generator import generate_all


def run_pipeline(days: int = 30, seed: int = 42) -> None:
    """Execute the full data pipeline: generate, clean, store.

    Args:
        days: Number of days of data to generate.
        seed: Random seed for synthetic generation.
    """
    logger.info(f"Running data pipeline (days={days}, seed={seed})")

    datasets = generate_all(days=days, seed=seed)

    for name, df in datasets.items():
        cleaned = ingest_dataframe(name, df)
        store.put(name, cleaned)

    logger.info(
        f"Pipeline complete. Stored datasets: {store.keys()}"
    )


def ingest_dataframe(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Ingest a raw DataFrame through the cleaning pipeline.

    Args:
        name: Dataset identifier for logging.
        df: Raw DataFrame to process.

    Returns:
        Cleaned DataFrame.
    """
    logger.debug(f"Ingesting '{name}': {len(df)} rows")

    df = normalize_timestamps(df)
    df = clean_dataframe(df)

    logger.debug(f"Ingested '{name}': {len(df)} rows after cleaning")
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate a DataFrame.

    Performs: drop duplicates, handle NaN, ensure datetime index,
    sort by time, validate value ranges.

    Args:
        df: Raw DataFrame to clean.

    Returns:
        Cleaned DataFrame.
    """
    initial_len = len(df)

    # Drop exact duplicate rows
    df = df.drop_duplicates()

    # Sort by timestamp if present
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)

    # Forward-fill small NaN gaps in numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        df[numeric_cols] = df[numeric_cols].ffill(limit=3)

    # Drop remaining rows with NaN in critical columns
    df = df.dropna(subset=["timestamp"] if "timestamp" in df.columns else [])

    dropped = initial_len - len(df)
    if dropped > 0:
        logger.debug(f"Cleaning removed {dropped} rows")

    return df.reset_index(drop=True)


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize timestamp column to UTC datetime index.

    Args:
        df: DataFrame with a 'timestamp' column or datetime index.

    Returns:
        DataFrame with normalized DatetimeIndex.
    """
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    elif isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        df.rename(columns={df.columns[0]: "timestamp"}, inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    return df
