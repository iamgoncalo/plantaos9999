"""In-memory DataStore backed by dictionaries of DataFrames.

Central data repository that holds all time-series data for the application.
Thread-safe read/write access for use with Dash callbacks.
"""

from __future__ import annotations

import threading

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
        logger.debug("DataStore initialized")

    def put(self, name: str, df: pd.DataFrame) -> None:
        """Store a DataFrame under the given name.

        Args:
            name: Dataset identifier (e.g., 'energy', 'comfort').
            df: DataFrame to store.
        """
        ...

    def get(self, name: str) -> pd.DataFrame | None:
        """Retrieve a DataFrame by name.

        Args:
            name: Dataset identifier.

        Returns:
            The stored DataFrame, or None if not found.
        """
        ...

    def keys(self) -> list[str]:
        """List all stored dataset names.

        Returns:
            List of dataset name strings.
        """
        ...

    def has(self, name: str) -> bool:
        """Check if a dataset exists.

        Args:
            name: Dataset identifier.

        Returns:
            True if dataset is stored.
        """
        ...

    def clear(self) -> None:
        """Remove all stored data."""
        ...


# Module-level singleton
store = DataStore()
