"""Stream fusion -- EMA smoothing of validated sensor events.

Maintains a per-zone exponential moving average for each metric.
Outlier events are silently skipped to avoid corrupting the
smoothed state.
"""

from __future__ import annotations

from collections import defaultdict

from core.validate import ValidatedEvent

# EMA state: zone_id -> {metric_name -> smoothed_value}
_ZONE_EMA: dict[str, dict[str, float]] = defaultdict(dict)

# Smoothing factor: higher = more weight on new readings
_ALPHA: float = 0.3


def fuse_event(event: ValidatedEvent) -> dict[str, float]:
    """Incorporate a validated event into the fused zone state.

    Outliers are ignored. The EMA formula is:
        new = alpha * value + (1 - alpha) * previous

    Args:
        event: A ValidatedEvent (outlier flag checked).

    Returns:
        Current fused metric dict for the event's zone.
    """
    if event.is_outlier:
        return dict(_ZONE_EMA.get(event.zone_id, {}))

    prev = _ZONE_EMA[event.zone_id].get(event.metric)
    if prev is None:
        _ZONE_EMA[event.zone_id][event.metric] = event.value
    else:
        _ZONE_EMA[event.zone_id][event.metric] = (
            _ALPHA * event.value + (1 - _ALPHA) * prev
        )
    return dict(_ZONE_EMA[event.zone_id])


def fuse_batch(
    events: list[ValidatedEvent],
) -> dict[str, dict[str, float]]:
    """Fuse a batch of validated events and return all zones touched.

    Args:
        events: List of ValidatedEvent objects.

    Returns:
        Dict mapping zone_id to its current fused state.
    """
    touched: set[str] = set()
    for event in events:
        fuse_event(event)
        touched.add(event.zone_id)
    return {zid: dict(_ZONE_EMA[zid]) for zid in touched}


def get_fused_state(zone_id: str) -> dict[str, float]:
    """Retrieve the current EMA-smoothed state for a zone.

    Args:
        zone_id: Building zone identifier.

    Returns:
        Dict of metric_name -> smoothed value (empty if unseen).
    """
    return dict(_ZONE_EMA.get(zone_id, {}))


def reset_fused_state() -> None:
    """Clear all fused state (e.g. on data regeneration)."""
    _ZONE_EMA.clear()


def set_alpha(alpha: float) -> None:
    """Update the EMA smoothing factor.

    Args:
        alpha: New alpha in (0, 1]. Higher = more responsive.
    """
    global _ALPHA
    _ALPHA = max(0.01, min(1.0, alpha))
