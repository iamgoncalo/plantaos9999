"""Synthetic occupancy and presence patterns.

Generates realistic occupancy data following Portuguese factory shifts
(6h-14h / 14h-22h), meeting patterns, lunch breaks (12h-13h),
and weekend minimal occupancy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_occupancy_data(
    zones: list[dict],
    days: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate occupancy data for all zones.

    Args:
        zones: List of zone dicts with 'id', 'capacity', 'zone_type' keys.
        days: Number of days of history.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, zone_id, occupant_count,
        occupancy_ratio, is_occupied.
    """
    rng = np.random.default_rng(seed)
    intervals_per_day = 288  # 5-min intervals
    n_timestamps = days * intervals_per_day

    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    timestamps = pd.date_range(start=start, periods=n_timestamps, freq="5min")

    hours = timestamps.hour + timestamps.minute / 60.0
    dow = timestamps.dayofweek
    is_weekend = dow >= 5

    # Only generate for zones with capacity > 0
    active_zones = [z for z in zones if z["capacity"] > 0]

    # Pre-generate event schedules for special zones
    event_schedule = _generate_event_schedule(active_zones, days, rng)

    all_records: list[pd.DataFrame] = []

    for zone in active_zones:
        zone_id = zone["id"]
        capacity = zone["capacity"]
        zone_type = zone["zone_type"]

        # Base occupancy ratio for each timestamp
        ratios = np.zeros(n_timestamps)

        for i in range(n_timestamps):
            h = hours[i]
            d = dow[i]
            we = is_weekend[i]
            day_idx = i // intervals_per_day

            if we:
                # Weekend: minimal occupancy (security/maintenance)
                ratios[i] = rng.uniform(0, 0.05) if 8 <= h <= 16 else 0.0
                continue

            # Check for special events on this zone/day/time
            event_ratio = _get_event_ratio(event_schedule, zone_id, day_idx, h)
            if event_ratio is not None:
                ratios[i] = event_ratio
                continue

            # Apply zone-type specific pattern
            ratios[i] = _shift_occupancy_pattern(h, d, zone_type)

        # Add noise only where there is expected occupancy
        noise = rng.normal(0, 0.08, n_timestamps)
        has_activity = ratios > 0.01
        ratios[has_activity] += noise[has_activity]
        ratios = np.clip(ratios, 0, 1.0)

        # Convert to occupant counts
        counts = np.round(ratios * capacity).astype(int)
        counts = np.clip(counts, 0, capacity)
        actual_ratios = counts / max(capacity, 1)

        zone_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "zone_id": zone_id,
                "occupant_count": counts,
                "occupancy_ratio": np.round(actual_ratios, 3),
                "is_occupied": counts > 0,
            }
        )
        all_records.append(zone_df)

    return pd.concat(all_records, ignore_index=True)


def _generate_event_schedule(
    zones: list[dict],
    days: int,
    rng: np.random.Generator,
) -> dict[str, list[tuple[int, float, float, float]]]:
    """Pre-generate special event blocks for multipurpose/dojo/meeting zones.

    Args:
        zones: Active zone list.
        days: Number of days.
        rng: Random number generator.

    Returns:
        Dict mapping zone_id to list of (day_idx, start_hour, end_hour, ratio).
    """
    schedule: dict[str, list[tuple[int, float, float, float]]] = {}

    for zone in zones:
        zone_id = zone["id"]
        zone_type = zone["zone_type"]
        events: list[tuple[int, float, float, float]] = []

        if zone_type == "multipurpose":
            # 2-3 large events per week
            for week in range(days // 7 + 1):
                n_events = rng.integers(2, 4)
                event_days = rng.choice(
                    range(week * 7, min((week + 1) * 7, days)),
                    size=min(n_events, min(5, days - week * 7)),
                    replace=False,
                )
                for ed in event_days:
                    start_h = rng.choice([9.0, 10.0, 14.0, 15.0])
                    duration = rng.uniform(2, 4)
                    ratio = rng.uniform(0.6, 0.95)
                    events.append((int(ed), start_h, start_h + duration, ratio))

        elif zone_type == "dojo":
            # 2-3 safety training sessions per week
            for week in range(days // 7 + 1):
                n_sessions = rng.integers(2, 4)
                session_days = rng.choice(
                    range(week * 7, min((week + 1) * 7, days)),
                    size=min(n_sessions, min(5, days - week * 7)),
                    replace=False,
                )
                for sd in session_days:
                    start_h = rng.choice([8.0, 9.0, 14.0, 15.0])
                    duration = rng.uniform(2, 3)
                    ratio = rng.uniform(0.5, 0.85)
                    events.append((int(sd), start_h, start_h + duration, ratio))

        elif zone_type == "meeting":
            # 3-5 meeting blocks per weekday
            for d in range(days):
                dow = (
                    pd.Timestamp.now().normalize() - pd.Timedelta(days=days - d)
                ).dayofweek
                if dow >= 5:
                    continue
                n_meetings = rng.integers(2, 6)
                used_hours: set[float] = set()
                for _ in range(n_meetings):
                    start_h = rng.choice(
                        [8.0, 9.0, 9.5, 10.0, 11.0, 14.0, 14.5, 15.0, 16.0]
                    )
                    if start_h in used_hours:
                        continue
                    used_hours.add(start_h)
                    duration = rng.choice([1.0, 1.5, 2.0])
                    ratio = rng.uniform(0.5, 0.9)
                    events.append((d, start_h, start_h + duration, ratio))

        elif zone_type == "auditorium":
            # ~2 sessions per week
            for week in range(days // 7 + 1):
                n_sessions = rng.integers(1, 3)
                session_days = rng.choice(
                    range(week * 7, min((week + 1) * 7, days)),
                    size=min(n_sessions, min(5, days - week * 7)),
                    replace=False,
                )
                for sd in session_days:
                    start_h = rng.choice([9.0, 10.0, 14.0, 15.0])
                    duration = rng.uniform(1.5, 3)
                    ratio = rng.uniform(0.5, 0.85)
                    events.append((int(sd), start_h, start_h + duration, ratio))

        if events:
            schedule[zone_id] = events

    return schedule


def _get_event_ratio(
    schedule: dict[str, list[tuple[int, float, float, float]]],
    zone_id: str,
    day_idx: int,
    hour: float,
) -> float | None:
    """Check if a zone has an event at the given day/time.

    Args:
        schedule: Pre-generated event schedule.
        zone_id: Zone to check.
        day_idx: Day index (0-based).
        hour: Fractional hour of day.

    Returns:
        Occupancy ratio if event is active, None otherwise.
    """
    events = schedule.get(zone_id, [])
    for day, start_h, end_h, ratio in events:
        if day == day_idx and start_h <= hour < end_h:
            return ratio
    return None


def _shift_occupancy_pattern(
    hour: float,
    day_of_week: int,
    zone_type: str,
) -> float:
    """Model occupancy based on shift schedule and zone type.

    Args:
        hour: Hour of day (fractional, e.g. 10.5 = 10:30).
        day_of_week: Day of week (0=Monday, 6=Sunday).
        zone_type: Zone classification.

    Returns:
        Expected occupancy ratio (0.0 to 1.0).
    """
    if day_of_week >= 5:
        return 0.0

    # Night hours: minimal
    if hour < 6 or hour >= 22:
        return 0.0

    if zone_type == "social":
        return _social_area_pattern(hour, day_of_week)

    if zone_type == "library":
        # Steady low-medium during business hours
        if 8 <= hour < 18:
            return 0.25 + 0.1 * np.sin(np.pi * (hour - 8) / 10)
        return 0.0

    if zone_type == "it_lab":
        # Steady during business hours, higher morning
        if 7 <= hour < 20:
            base = 0.55
            if 9 <= hour < 12:
                base = 0.70
            elif 14 <= hour < 17:
                base = 0.65
            return base
        return 0.0

    if zone_type == "reception":
        # 1-3 people during business hours with peaks at shift change
        if 6 <= hour < 7:
            return 0.4  # Morning arrival
        if 13.5 <= hour < 14.5:
            return 0.6  # Shift change
        if 7 <= hour < 20:
            return 0.3
        return 0.0

    if zone_type == "office":
        # Steady during business hours
        if 8 <= hour < 18:
            return 0.65
        if 7 <= hour < 8:
            return 0.3
        return 0.0

    if zone_type == "production":
        # Follows shifts
        if 6 <= hour < 14:
            return 0.45
        if 14 <= hour < 22:
            return 0.40
        return 0.0

    if zone_type == "circulation":
        # Proportional to building activity, peaks at transitions
        if 6 <= hour < 6.5:
            return 0.4  # Morning arrival
        if 13.5 <= hour < 14.5:
            return 0.5  # Shift change
        if 12 <= hour < 13:
            return 0.4  # Lunch movement
        if 6 <= hour < 22:
            return 0.2
        return 0.0

    # Training rooms: shift-aligned (default for training, archive, etc.)
    return _training_pattern(hour)


def _training_pattern(hour: float) -> float:
    """Model training room occupancy aligned to factory shifts.

    Args:
        hour: Fractional hour of day.

    Returns:
        Expected occupancy ratio.
    """
    # Morning shift training: 7-13h
    if 6 <= hour < 6.5:
        return (hour - 6) * 1.2  # Ramp up
    if 6.5 <= hour < 12:
        return 0.70
    if 12 <= hour < 13:
        return 0.15  # Lunch break
    if 13 <= hour < 13.5:
        return 0.30  # Transition

    # Afternoon shift training: 14-21h
    if 13.5 <= hour < 14:
        return (hour - 13.5) * 1.2  # Ramp up
    if 14 <= hour < 17:
        return 0.65
    if 17 <= hour < 21:
        return 0.50
    if 21 <= hour < 21.5:
        return (21.5 - hour) * 1.0  # Ramp down

    return 0.0


def _meeting_room_pattern(hour: float, day_of_week: int) -> float:
    """Model meeting room usage patterns.

    Args:
        hour: Hour of day (fractional).
        day_of_week: Day of week.

    Returns:
        Expected occupancy ratio.
    """
    if day_of_week >= 5:
        return 0.0

    # Between scheduled meetings: low background
    if 8 <= hour < 18:
        return 0.15
    return 0.0


def _social_area_pattern(hour: float, day_of_week: int) -> float:
    """Model social area (copa, library) usage with lunch peak.

    Args:
        hour: Hour of day (fractional).
        day_of_week: Day of week.

    Returns:
        Expected occupancy ratio.
    """
    if day_of_week >= 5:
        return 0.0

    # Coffee break mornings
    if 9.5 <= hour < 10.5:
        return 0.5

    # Lunch peak
    if 12 <= hour < 12.25:
        return 0.6  # Starting to fill
    if 12.25 <= hour < 13:
        return 0.9  # Peak lunch
    if 13 <= hour < 13.25:
        return 0.5  # Clearing out

    # Afternoon coffee
    if 15 <= hour < 16:
        return 0.45

    # General low activity during business hours
    if 7 <= hour < 20:
        return 0.15

    return 0.0
