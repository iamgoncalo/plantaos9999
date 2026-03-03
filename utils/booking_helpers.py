"""Booking helper functions — pure logic, no Dash dependencies.

Contains room scoring, conflict detection, time-slot computation,
equipment matching, and comfort/energy projection helpers used by
the Smart Booking page callbacks.
"""

from __future__ import annotations

from datetime import date

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones


def score_room(
    zone_id: str,
    zone_capacity: int,
    zone_type: str,
    requested_people: int,
    needs_projector: bool = False,
    needs_computers: bool = False,
    needs_quiet: bool = False,
    comfort_data: dict | None = None,
) -> int:
    """Score a room 0-100 for a booking request.

    Args:
        zone_id: Zone identifier.
        zone_capacity: Maximum room capacity.
        zone_type: Zone type string (e.g. 'training', 'it_lab').
        requested_people: Number of occupants requested.
        needs_projector: Whether a projector is required.
        needs_computers: Whether computers are required.
        needs_quiet: Whether a quiet zone is required.
        comfort_data: Optional dict with current comfort metrics.

    Returns:
        Integer score between 0 and 100.
    """
    score = 50  # base

    # Capacity fit: 80% utilization is optimal
    if zone_capacity == 0:
        return 0  # not bookable
    ratio = requested_people / zone_capacity
    if ratio > 1.0:
        return 0  # over capacity, can't book
    elif 0.6 <= ratio <= 0.9:
        score += 30  # excellent fit
    elif 0.4 <= ratio < 0.6:
        score += 20  # good fit
    elif ratio < 0.3:
        score += 5  # wasteful
    else:
        score += 15  # acceptable

    # Equipment matching
    if needs_computers and zone_type == "it_lab":
        score += 15
    if needs_projector and zone_type in (
        "training",
        "multipurpose",
        "auditorium",
    ):
        score += 10
    if needs_quiet and zone_type in ("meeting", "archive"):
        score += 10

    # Comfort bonus (if data available)
    if comfort_data:
        temp = comfort_data.get("temperature_c")
        if temp and 20 <= temp <= 24:
            score += 5

    return min(100, max(0, score))


def has_booking_conflict(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    bookings: list[dict],
) -> bool:
    """Check if a proposed booking conflicts with existing ones.

    Args:
        zone_id: Zone identifier.
        booking_date: Date of the proposed booking.
        start_hour: Start hour (6-22).
        duration: Duration in hours.
        bookings: Existing bookings list.

    Returns:
        True if there is a time conflict.
    """
    date_str = str(booking_date)
    new_start = start_hour
    new_end = start_hour + duration

    for b in bookings:
        if b.get("zone_id") != zone_id:
            continue
        if b.get("date") != date_str:
            continue
        b_start = b.get("start_hour", 0)
        b_end = b_start + b.get("duration", 0)
        if new_start < b_end and new_end > b_start:
            return True

    return False


def compute_requirement_bonus(
    zone_id: str,
    zone_capacity: int,
    requirements: list[str],
) -> float:
    """Compute bonus points for matching room equipment.

    Args:
        zone_id: Zone identifier string.
        zone_capacity: Zone max capacity.
        requirements: List of requirement strings.

    Returns:
        Total bonus points to add to the room score.
    """
    if not requirements:
        return 0.0

    bonus = 0.0
    zone_id_lower = zone_id.lower()

    if "computers" in requirements and "informatica" in zone_id_lower:
        bonus += 10.0
    if "projector" in requirements and (
        "multiusos" in zone_id_lower or "auditorio" in zone_id_lower
    ):
        bonus += 10.0
    if "quiet" in requirements and zone_capacity < 20:
        bonus += 5.0

    return bonus


def compute_room_metrics(
    area_m2: float,
    capacity: int,
    people: int,
    duration: int,
) -> dict:
    """Compute detailed comfort, energy, and capacity metrics.

    Args:
        area_m2: Room area in square meters.
        capacity: Maximum occupancy.
        people: Requested occupant count.
        duration: Duration in hours.

    Returns:
        Dict with comfort_score, energy_score, energy_kwh,
        energy_cost, capacity_fit, avg_temp, peak_co2.
    """
    steps = duration * 4
    temps, co2s = fallback_projection(people, area_m2, duration, steps)
    avg_temp = sum(temps) / len(temps) if temps else 22.0
    avg_co2 = sum(co2s) / len(co2s) if co2s else 500.0

    temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    comfort_score = (temp_score + co2_score) / 2.0

    hvac_load_kw = (
        DEFAULT_AFI_CONFIG.air_density
        * DEFAULT_AFI_CONFIG.air_specific_heat
        * area_m2
        * DEFAULT_AFI_CONFIG.ceiling_height_m
        * temp_dev
        / (3600 * DEFAULT_AFI_CONFIG.hvac_efficiency)
    )
    energy_kwh = max(0.5, hvac_load_kw * duration + people * 0.05 * duration)
    energy_cost = energy_kwh * DEFAULT_AFI_CONFIG.cost_per_kwh
    energy_score = max(0.0, 100.0 - energy_cost * 20.0)

    capacity_fit = 1.0 - abs(capacity - people) / capacity if capacity else 0.0
    capacity_fit_score = capacity_fit * 100.0

    return {
        "comfort_score": round(comfort_score, 1),
        "energy_score": round(energy_score, 1),
        "energy_kwh": round(energy_kwh, 1),
        "energy_cost": round(energy_cost, 2),
        "capacity_fit": round(capacity_fit_score, 1),
        "avg_temp": round(avg_temp, 1),
        "peak_co2": round(max(co2s) if co2s else 500, 0),
    }


def fallback_projection(
    people: int,
    area_m2: float,
    duration: int,
    steps: int,
) -> tuple[list[float], list[float]]:
    """Generate simplified temperature and CO2 projections.

    Args:
        people: Number of occupants.
        area_m2: Room area in square meters.
        duration: Booking duration in hours.
        steps: Number of 15-minute intervals.

    Returns:
        Tuple of (temperature list, CO2 list) with steps+1 entries.
    """
    base_temp = DEFAULT_AFI_CONFIG.optimal_temperature_c
    base_co2 = DEFAULT_AFI_CONFIG.optimal_co2_ppm

    heat_per_person_kw = 0.08
    co2_per_person_ppm_per_step = 5.0
    thermal_mass = area_m2 * DEFAULT_AFI_CONFIG.ceiling_height_m * 1.2
    ventilation_decay = 0.02

    temps = [base_temp]
    co2s = [base_co2]

    for _i in range(steps):
        heat_input = people * heat_per_person_kw * 0.25
        temp_rise = heat_input / thermal_mass * 100
        hvac_correction = (temps[-1] - base_temp) * 0.3
        new_temp = temps[-1] + temp_rise - hvac_correction
        temps.append(round(new_temp, 2))

        co2_input = people * co2_per_person_ppm_per_step
        co2_removal = (co2s[-1] - 400) * ventilation_decay
        new_co2 = co2s[-1] + co2_input - co2_removal
        co2s.append(round(max(400.0, new_co2), 1))

    return temps, co2s


def find_optimal_room(people: int) -> str:
    """Find the best room for the given occupant count.

    Args:
        people: Expected number of occupants.

    Returns:
        Display name of the optimal zone.
    """
    candidates = []
    for zone in get_monitored_zones():
        if zone.capacity >= people:
            distortion = (zone.capacity - people) / zone.capacity
            candidates.append((distortion, zone))

    if not candidates:
        all_zones = get_monitored_zones()
        if all_zones:
            return max(all_zones, key=lambda z: z.capacity).name
        return "N/A"

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].name
