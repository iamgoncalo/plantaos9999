"""Booking helper functions — pure logic for scoring, conflicts, projections.

Used by booking page callbacks. Contains no Dash callback decorators.
"""

from __future__ import annotations

from datetime import date

from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones
from core.afi.aco import ACOConfig, aco_optimize


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
    """Score a room 0-100 for a booking request."""
    score = 50
    if zone_capacity == 0:
        return 0
    ratio = requested_people / zone_capacity
    if ratio > 1.0:
        return 0
    elif 0.6 <= ratio <= 0.9:
        score += 30
    elif 0.4 <= ratio < 0.6:
        score += 20
    elif ratio < 0.3:
        score += 5
    else:
        score += 15
    if needs_computers and zone_type == "it_lab":
        score += 15
    if needs_projector and zone_type in ("training", "multipurpose", "auditorium"):
        score += 10
    if needs_quiet and zone_type in ("meeting", "archive"):
        score += 10
    if comfort_data:
        temp = comfort_data.get("temperature_c")
        if temp and 20 <= temp <= 24:
            score += 5

    # ACO routing penalty: farther rooms get a small deduction
    route_cost = _aco_routing_score(zone_id)
    score -= int(route_cost * 0.1 * 10)  # ~10% weight on routing distance

    return min(100, max(0, score))


def has_booking_conflict(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    bookings: list[dict],
) -> bool:
    """Check if a proposed booking conflicts with existing ones."""
    date_str = str(booking_date)
    new_start, new_end = start_hour, start_hour + duration
    for b in bookings:
        if b.get("zone_id") != zone_id or b.get("date") != date_str:
            continue
        b_start = b.get("start_hour", 0)
        if new_start < b_start + b.get("duration", 0) and new_end > b_start:
            return True
    return False


def compute_requirement_bonus(
    zone_id: str,
    zone_capacity: int,
    requirements: list[str],
) -> float:
    """Compute bonus points for matching room equipment."""
    if not requirements:
        return 0.0
    bonus, zid = 0.0, zone_id.lower()
    if "computers" in requirements and "informatica" in zid:
        bonus += 10.0
    if "projector" in requirements and ("multiusos" in zid or "auditorio" in zid):
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
    """Compute detailed comfort, energy, and capacity metrics."""
    steps = duration * 4
    temps, co2s = fallback_projection(people, area_m2, duration, steps)
    avg_temp = sum(temps) / len(temps) if temps else 22.0
    avg_co2 = sum(co2s) / len(co2s) if co2s else 500.0
    cfg = DEFAULT_AFI_CONFIG
    temp_dev = abs(avg_temp - cfg.optimal_temperature_c)
    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - cfg.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    comfort_score = (temp_score + co2_score) / 2.0
    hvac_kw = (
        cfg.air_density
        * cfg.air_specific_heat
        * area_m2
        * cfg.ceiling_height_m
        * temp_dev
        / (3600 * cfg.hvac_efficiency)
    )
    energy_kwh = max(0.5, hvac_kw * duration + people * 0.05 * duration)
    energy_cost = energy_kwh * cfg.cost_per_kwh
    cap_fit = (1.0 - abs(capacity - people) / capacity) * 100 if capacity else 0.0
    return {
        "comfort_score": round(comfort_score, 1),
        "energy_score": round(max(0.0, 100.0 - energy_cost * 20.0), 1),
        "energy_kwh": round(energy_kwh, 1),
        "energy_cost": round(energy_cost, 2),
        "capacity_fit": round(cap_fit, 1),
        "avg_temp": round(avg_temp, 1),
        "peak_co2": round(max(co2s) if co2s else 500, 0),
    }


def fallback_projection(
    people: int,
    area_m2: float,
    duration: int,
    steps: int,
) -> tuple[list[float], list[float]]:
    """Generate simplified temperature and CO2 projections."""
    cfg = DEFAULT_AFI_CONFIG
    base_temp, base_co2 = cfg.optimal_temperature_c, cfg.optimal_co2_ppm
    thermal_mass = area_m2 * cfg.ceiling_height_m * 1.2
    temps, co2s = [base_temp], [base_co2]
    for _ in range(steps):
        heat = people * 0.08 * 0.25
        rise = heat / thermal_mass * 100
        correction = (temps[-1] - base_temp) * 0.3
        temps.append(round(temps[-1] + rise - correction, 2))
        co2_in = people * 5.0
        co2_out = (co2s[-1] - 400) * 0.02
        co2s.append(round(max(400.0, co2s[-1] + co2_in - co2_out), 1))
    return temps, co2s


def _aco_routing_score(zone_id: str) -> float:
    """Compute ACO routing cost from building entrance to a zone.

    Uses the zone adjacency graph from afi_engine to find shortest path
    from the hall (entrance) to the target zone. Returns normalized cost
    where lower is better.

    Args:
        zone_id: Target zone ID.

    Returns:
        Routing cost (0.0 = adjacent to entrance, higher = farther).
    """
    try:
        from core.afi_engine import _ZONE_ADJACENCY

        # Entrance is the hall on the target floor
        floor = "p0" if zone_id.startswith("p0") else "p1"
        entrance = f"{floor}_hall" if floor == "p0" else f"{floor}_circulacao"

        if entrance not in _ZONE_ADJACENCY or zone_id not in _ZONE_ADJACENCY:
            return 0.0

        result = aco_optimize(
            adjacency=_ZONE_ADJACENCY,
            source=entrance,
            targets=[zone_id],
            config=ACOConfig(n_ants=10, max_iter=10, seed=42),
        )

        if result.best_route.path:
            return result.best_route.cost
    except Exception as exc:
        logger.debug(f"ACO routing skipped for {zone_id}: {exc}")
    return 0.0


def find_optimal_room(people: int) -> str:
    """Find the best room for the given occupant count."""
    candidates = [
        ((z.capacity - people) / z.capacity, z)
        for z in get_monitored_zones()
        if z.capacity >= people
    ]
    if not candidates:
        zones = get_monitored_zones()
        return max(zones, key=lambda z: z.capacity).name if zones else "N/A"
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].name


def compute_forward_analysis(
    zone_id: str,
    zone_area: float,
    zone_capacity: int,
    people: int,
    duration: int,
) -> dict:
    """Compute forward projection data for a booking analysis.

    Returns dict with: projected_energy, predicted_comfort,
    projected_perf, optimal_room, temps, co2s, peak_co2.
    """
    cfg = DEFAULT_AFI_CONFIG
    steps = duration * 4
    temps, co2s = fallback_projection(people, zone_area, duration, steps)
    avg_temp = sum(temps) / len(temps)
    avg_co2 = sum(co2s) / len(co2s)
    temp_dev = abs(avg_temp - cfg.optimal_temperature_c)
    hvac_kw = (
        cfg.air_density
        * cfg.air_specific_heat
        * zone_area
        * cfg.ceiling_height_m
        * temp_dev
        / (3600 * cfg.hvac_efficiency)
    )
    projected_energy = max(0.5, hvac_kw * duration + people * 0.05 * duration)
    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - cfg.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    comfort = (temp_score + co2_score) / 2.0
    return {
        "projected_energy": projected_energy,
        "energy_cost": projected_energy * cfg.cost_per_kwh,
        "predicted_comfort": comfort,
        "projected_perf": comfort * 0.85 + 15.0,
        "optimal_room": find_optimal_room(people),
        "temps": temps,
        "co2s": co2s,
        "peak_co2": max(co2s),
        "occ_ratio": people / zone_capacity if zone_capacity > 0 else 1.0,
    }


def compute_backward_analysis(
    energy_df: object,
    comfort_df: object,
    duration: int,
    people: int,
) -> dict:
    """Compute backward analysis metrics from historical data.

    Returns dict with: energy_kwh, comfort_index, performance, added_value,
    avg_temp, avg_co2.
    """
    cfg = DEFAULT_AFI_CONFIG
    energy_kwh = 0.0
    if energy_df is not None and not energy_df.empty:
        if "total_kwh" in energy_df.columns:
            energy_kwh = float(energy_df["total_kwh"].sum())

    comfort_index, avg_temp, avg_co2 = 50.0, None, None
    if comfort_df is not None and not comfort_df.empty:
        scores = []
        if "temperature_c" in comfort_df.columns:
            avg_temp = float(comfort_df["temperature_c"].mean())
            scores.append(
                max(0.0, 100.0 - abs(avg_temp - cfg.optimal_temperature_c) * 15.0)
            )
        if "co2_ppm" in comfort_df.columns:
            avg_co2 = float(comfort_df["co2_ppm"].mean())
            scores.append(
                max(0.0, 100.0 - max(0.0, avg_co2 - cfg.optimal_co2_ppm) * 0.1)
            )
        if scores:
            comfort_index = sum(scores) / len(scores)

    perf = comfort_index * 0.85 + 15.0
    added = (perf / 100.0) * cfg.avg_hourly_wage * duration * people
    return {
        "energy_kwh": energy_kwh,
        "comfort_index": comfort_index,
        "performance": perf,
        "added_value": added,
        "avg_temp": avg_temp,
        "avg_co2": avg_co2,
    }
