"""Schema + range checks + outlier tagging for sensor events.

Each metric has predefined physical bounds. Events outside those
bounds are tagged as outliers so the fusion stage can skip them.
"""

from __future__ import annotations

from core.ingest import RawEvent

# Physical plausibility ranges per metric
_RANGES: dict[str, tuple[float, float]] = {
    "temperature_c": (-10.0, 50.0),
    "humidity_pct": (0.0, 100.0),
    "co2_ppm": (200.0, 5000.0),
    "illuminance_lux": (0.0, 10000.0),
    "occupancy_count": (0.0, 500.0),
    "total_kwh": (0.0, 1000.0),
}


class ValidatedEvent(RawEvent):
    """A sensor event enriched with validation metadata.

    Attributes:
        is_outlier: True if the reading fell outside physical bounds.
        validation_note: Human-readable explanation if flagged.
    """

    is_outlier: bool = False
    validation_note: str = ""


def validate_event(event: RawEvent) -> ValidatedEvent:
    """Run range checks on a raw event and return a tagged copy.

    Args:
        event: The incoming RawEvent to validate.

    Returns:
        ValidatedEvent with is_outlier and validation_note set.
    """
    bounds = _RANGES.get(event.metric)
    is_outlier = False
    note = ""
    if bounds:
        lo, hi = bounds
        if event.value < lo or event.value > hi:
            is_outlier = True
            note = f"{event.value} outside [{lo}, {hi}]"
    return ValidatedEvent(
        **event.model_dump(),
        is_outlier=is_outlier,
        validation_note=note,
    )


def validate_batch(
    events: list[RawEvent],
) -> list[ValidatedEvent]:
    """Validate a batch of raw events.

    Args:
        events: List of RawEvent objects.

    Returns:
        List of ValidatedEvent objects with outlier tags.
    """
    return [validate_event(e) for e in events]


def get_metric_bounds(metric: str) -> tuple[float, float] | None:
    """Look up the valid range for a metric.

    Args:
        metric: Metric name string.

    Returns:
        Tuple of (lower, upper) bounds or None if unknown.
    """
    return _RANGES.get(metric)
