"""Raw event ingestion -- receives sensor readings into ring buffer.

Provides a bounded in-memory deque for incoming RawEvent objects.
Events are consumed via drain_events() by the validation/fusion
stages downstream.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime

from pydantic import BaseModel, Field


class RawEvent(BaseModel):
    """A single raw sensor reading before validation.

    Attributes:
        sensor_id: Hardware identifier of the sensor.
        zone_id: Building zone where the sensor is installed.
        metric: Metric name (e.g. 'temperature_c', 'co2_ppm').
        value: Numeric reading value.
        timestamp: When the reading was taken.
        quality: Signal quality factor in [0, 1].
    """

    sensor_id: str
    zone_id: str
    metric: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    quality: float = 1.0


_BUFFER: deque[RawEvent] = deque(maxlen=10_000)


def ingest_event(event: RawEvent) -> None:
    """Append a raw sensor event to the ring buffer.

    Args:
        event: Validated RawEvent to enqueue.
    """
    _BUFFER.append(event)


def drain_events(max_count: int = 500) -> list[RawEvent]:
    """Pop up to max_count events from the buffer (FIFO).

    Args:
        max_count: Maximum number of events to drain.

    Returns:
        List of RawEvent objects removed from the buffer.
    """
    events: list[RawEvent] = []
    while _BUFFER and len(events) < max_count:
        events.append(_BUFFER.popleft())
    return events


def buffer_size() -> int:
    """Return the current number of events waiting in the buffer.

    Returns:
        Integer count of buffered events.
    """
    return len(_BUFFER)
