"""In-memory DataStore backed by dictionaries of DataFrames.

Central data repository that holds all time-series data for the application.
Thread-safe read/write access for use with Dash callbacks.
"""

from __future__ import annotations

import threading
from datetime import datetime

import pandas as pd
from loguru import logger


class DataStore:
    """In-memory store holding DataFrames keyed by dataset name.

    Provides thread-safe access to time-series data for energy, comfort,
    occupancy, and events. Designed for single-process Dash applications.
    """

    def __init__(self) -> None:
        """Initialize an empty DataStore."""
        self._data: dict[str, pd.DataFrame] = {}
        self._lock = threading.Lock()
        self._version: int = 0
        logger.debug("DataStore initialized")

    @property
    def version(self) -> int:
        """Return the current data version (incremented on each put)."""
        return self._version

    def put(self, name: str, df: pd.DataFrame) -> None:
        """Store a DataFrame under the given name.

        Args:
            name: Dataset identifier (e.g., 'energy', 'comfort').
            df: DataFrame to store.
        """
        with self._lock:
            self._data[name] = df
            self._version += 1
            logger.debug(f"Stored '{name}': {len(df)} rows, {list(df.columns)}")

    def get(self, name: str) -> pd.DataFrame:
        """Retrieve a DataFrame by name.

        Args:
            name: Dataset identifier.

        Returns:
            The stored DataFrame, or an empty DataFrame if not found.
        """
        with self._lock:
            df = self._data.get(name)
            if df is None:
                logger.debug(f"Dataset '{name}' not found, returning empty DataFrame")
                return pd.DataFrame()
            return df.copy()

    def keys(self) -> list[str]:
        """List all stored dataset names.

        Returns:
            List of dataset name strings.
        """
        with self._lock:
            return list(self._data.keys())

    def has(self, name: str) -> bool:
        """Check if a dataset exists.

        Args:
            name: Dataset identifier.

        Returns:
            True if dataset is stored.
        """
        with self._lock:
            return name in self._data

    def clear(self) -> None:
        """Remove all stored data."""
        with self._lock:
            self._data.clear()
            logger.debug("DataStore cleared")

    def get_zone_data(self, name: str, zone_id: str) -> pd.DataFrame:
        """Retrieve data for a specific zone from a dataset.

        Args:
            name: Dataset identifier (e.g., 'energy', 'comfort').
            zone_id: The zone identifier to filter by.

        Returns:
            Filtered DataFrame (empty if dataset not found or zone missing).
        """
        df = self.get(name)
        if df.empty or "zone_id" not in df.columns:
            return df
        return df[df["zone_id"] == zone_id].reset_index(drop=True)

    def get_time_range(
        self,
        name: str,
        start: datetime | pd.Timestamp,
        end: datetime | pd.Timestamp,
    ) -> pd.DataFrame:
        """Retrieve data within a time range from a dataset.

        Args:
            name: Dataset identifier.
            start: Start of the time range (inclusive).
            end: End of the time range (inclusive).

        Returns:
            Filtered DataFrame (empty if dataset not found).
        """
        df = self.get(name)
        if df.empty:
            return df
        if "timestamp" in df.columns:
            mask = (df["timestamp"] >= pd.Timestamp(start)) & (
                df["timestamp"] <= pd.Timestamp(end)
            )
            return df[mask].reset_index(drop=True)
        return df

    def get_latest(self, name: str, n: int = 1) -> pd.DataFrame:
        """Retrieve the most recent n rows from a dataset.

        Args:
            name: Dataset identifier.
            n: Number of most recent rows to return.

        Returns:
            DataFrame with last n rows (empty if dataset not found).
        """
        df = self.get(name)
        if df.empty:
            return df
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp")
        return df.tail(n).reset_index(drop=True)


# Module-level singleton
store = DataStore()
