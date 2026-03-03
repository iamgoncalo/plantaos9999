"""Master synthetic data generator.

Orchestrates all profile generators (energy, comfort, occupancy, events)
to produce a coherent set of time-series data for the CFT building.
Generates 30 days of history at configurable intervals.
"""

from __future__ import annotations


import numpy as np
import pandas as pd
from loguru import logger

from config.building import CFT_BUILDING
from data.synthetic.comfort import generate_comfort_data
from data.synthetic.energy import generate_energy_data
from data.synthetic.events import generate_shift_schedule, generate_weather
from data.synthetic.occupancy import generate_occupancy_data


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
    logger.info(f"Generating {days} days of synthetic data (seed={seed})")

    # Extract zone info as list of dicts
    zones = _zones_as_dicts()

    # Step 1: External events (no dependencies)
    logger.info("Generating weather data...")
    weather_df = generate_weather(days=days, seed=seed)
    logger.info(f"  Weather: {len(weather_df)} rows")

    logger.info("Generating shift schedule...")
    schedule_df = generate_shift_schedule(days=days)
    logger.info(f"  Schedule: {len(schedule_df)} rows")

    # Step 2: Occupancy (depends on schedule for weekday/weekend)
    logger.info("Generating occupancy data...")
    occupancy_df = generate_occupancy_data(zones=zones, days=days, seed=seed)
    logger.info(f"  Occupancy: {len(occupancy_df)} rows")

    # Step 3: Energy (depends on weather + occupancy)
    logger.info("Generating energy data...")
    energy_df = generate_energy_data(
        zones=zones,
        days=days,
        interval_min=15,
        seed=seed,
        weather_df=weather_df,
        occupancy_df=occupancy_df,
    )
    logger.info(f"  Energy: {len(energy_df)} rows")

    # Step 4: Comfort (depends on weather + occupancy)
    logger.info("Generating comfort data...")
    comfort_df = generate_comfort_data(
        zones=zones,
        days=days,
        interval_min=5,
        seed=seed,
        weather_df=weather_df,
        occupancy_df=occupancy_df,
    )
    logger.info(f"  Comfort: {len(comfort_df)} rows")

    logger.info("Synthetic data generation complete")

    return {
        "energy": energy_df,
        "comfort": comfort_df,
        "occupancy": occupancy_df,
        "weather": weather_df,
        "schedule": schedule_df,
    }


def generate_realtime_tick(
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate a single timestamp of data for live simulation.

    Produces one row per zone for each data type, using current time.

    Args:
        seed: Optional seed for reproducibility. Uses current time if None.

    Returns:
        Dict with same keys as generate_all but single-row DataFrames.
    """
    now = pd.Timestamp.now().floor("5min")
    actual_seed = seed if seed is not None else int(now.timestamp()) % (2**31)
    rng = np.random.default_rng(actual_seed)

    zones = _zones_as_dicts()
    hour = now.hour + now.minute / 60.0
    dow = now.dayofweek
    is_weekend = dow >= 5

    # Weather tick
    outdoor_temp = 13.0 - 5.0 * np.cos(2 * np.pi * (hour - 5) / 24)
    outdoor_temp += rng.normal(0, 0.5)
    weather_tick = pd.DataFrame(
        {
            "timestamp": [now],
            "outdoor_temp_c": [round(outdoor_temp, 1)],
            "outdoor_humidity_pct": [round(70 + rng.normal(0, 5), 1)],
            "solar_radiation_w_m2": [
                round(
                    max(
                        0,
                        400 * np.sin(np.pi * max(0, hour - 7) / 12)
                        if 7 <= hour <= 19
                        else 0,
                    ),
                    0,
                )
            ],
            "wind_speed_ms": [round(4.0 + rng.normal(0, 1), 1)],
            "is_raining": [bool(rng.random() < 0.15)],
        }
    )

    # Schedule tick
    shift = (
        "morning" if 6 <= hour < 14 else ("afternoon" if 14 <= hour < 22 else "night")
    )
    schedule_tick = pd.DataFrame(
        {
            "timestamp": [now],
            "shift": [shift],
            "is_business_hours": [6 <= hour < 22],
            "is_weekend": [is_weekend],
        }
    )

    # Occupancy tick
    occ_records = []
    for z in zones:
        if z["capacity"] == 0:
            continue
        base_ratio = 0.0
        if not is_weekend and 6 <= hour < 22:
            base_ratio = rng.uniform(0.3, 0.7)
        count = int(round(base_ratio * z["capacity"]))
        occ_records.append(
            {
                "timestamp": now,
                "zone_id": z["id"],
                "occupant_count": count,
                "occupancy_ratio": round(count / max(z["capacity"], 1), 3),
                "is_occupied": count > 0,
            }
        )
    occupancy_tick = pd.DataFrame(occ_records)

    # Energy tick
    energy_records = []
    for z in zones:
        area = z["area_m2"]
        base = area * 0.12 / 96  # ~0.12 kWh/m²/day average
        factor = 0.8 if 6 <= hour < 22 and not is_weekend else 0.1
        total = base * factor * (1 + rng.normal(0, 0.1))
        energy_records.append(
            {
                "timestamp": now,
                "zone_id": z["id"],
                "hvac_kwh": round(total * 0.60, 4),
                "lighting_kwh": round(total * 0.20, 4),
                "equipment_kwh": round(total * 0.15, 4),
                "other_kwh": round(total * 0.05, 4),
                "total_kwh": round(total, 4),
            }
        )
    energy_tick = pd.DataFrame(energy_records)

    # Comfort tick
    comfort_records = []
    for z in zones:
        if not z.get("has_sensors", True):
            continue
        occ_ratio = rng.uniform(0.2, 0.6) if not is_weekend and 6 <= hour < 22 else 0.0
        temp = 22.0 + occ_ratio * 2 + (outdoor_temp - 22) * 0.1 + rng.normal(0, 0.3)
        humidity = 50 + occ_ratio * 8 + rng.normal(0, 2)
        co2 = 400 + occ_ratio * z.get("capacity", 10) * 40 * 0.5 + rng.normal(0, 15)
        lux = (400 if 7 <= hour < 21 else 10) + rng.normal(0, 20)
        comfort_records.append(
            {
                "timestamp": now,
                "zone_id": z["id"],
                "temperature_c": round(float(np.clip(temp, 14, 32)), 1),
                "humidity_pct": round(float(np.clip(humidity, 30, 85)), 1),
                "co2_ppm": int(np.clip(co2, 350, 2000)),
                "illuminance_lux": int(max(0, lux)),
            }
        )
    comfort_tick = pd.DataFrame(comfort_records)

    return {
        "energy": energy_tick,
        "comfort": comfort_tick,
        "occupancy": occupancy_tick,
        "weather": weather_tick,
        "schedule": schedule_tick,
    }


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
    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    n = days * (24 * 60 // interval_minutes)
    return pd.date_range(start=start, periods=n, freq=f"{interval_minutes}min")


def _zones_as_dicts() -> list[dict]:
    """Extract zone info from building config as list of dicts.

    Returns:
        List of zone dicts with keys: id, name, floor, area_m2,
        capacity, zone_type, has_hvac, has_sensors.
    """
    return [
        {
            "id": z.id,
            "name": z.name,
            "floor": z.floor,
            "area_m2": z.area_m2,
            "capacity": z.capacity,
            "zone_type": z.zone_type.value,
            "has_hvac": z.has_hvac,
            "has_sensors": z.has_sensors,
        }
        for z in CFT_BUILDING.all_zones
    ]


def _print_summary(datasets: dict[str, pd.DataFrame]) -> None:
    """Print summary statistics for each dataset.

    Args:
        datasets: Dict of DataFrames from generate_all.
    """
    for name, df in datasets.items():
        print(f"\n{'=' * 60}")
        print(f"  {name.upper()}")
        print(f"{'=' * 60}")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {list(df.columns)}")

        if "timestamp" in df.columns:
            print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

        if "zone_id" in df.columns:
            print(f"  Zones: {df['zone_id'].nunique()}")

        # Print numeric column stats
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            print(
                f"  {col}: min={df[col].min():.2f}, "
                f"max={df[col].max():.2f}, "
                f"mean={df[col].mean():.2f}"
            )

        print("\n  Sample (5 rows):")
        print(df.head(5).to_string(index=False))


if __name__ == "__main__":
    logger.info("Generating synthetic data...")
    datasets = generate_all()
    _print_summary(datasets)

    # Building-level daily energy check
    energy = datasets["energy"]
    daily_total = energy.groupby(energy["timestamp"].dt.date)["total_kwh"].sum()
    print(f"\n{'=' * 60}")
    print("  DAILY ENERGY TOTALS (kWh)")
    print(f"{'=' * 60}")
    print(f"  Min: {daily_total.min():.1f} kWh")
    print(f"  Max: {daily_total.max():.1f} kWh")
    print(f"  Mean: {daily_total.mean():.1f} kWh")

    # Building-level peak occupancy check
    occ = datasets["occupancy"]
    building_occ = occ.groupby("timestamp")["occupant_count"].sum()
    print(f"\n{'=' * 60}")
    print("  BUILDING OCCUPANCY")
    print(f"{'=' * 60}")
    print(f"  Peak: {building_occ.max()}")
    print(f"  Mean (business hours): {building_occ[building_occ > 10].mean():.0f}")
    print(f"  Night minimum: {building_occ.min()}")

    logger.info("Done.")
