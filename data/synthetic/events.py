"""Synthetic event generation for weather, schedules, and holidays.

Generates external events that influence building behavior:
weather conditions for March in Aveiro, shift schedule changes,
and Portuguese public holiday markers.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


def generate_weather(
    days: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic weather data for Aveiro in March.

    March in Aveiro: 8-18°C, occasional rain, humidity 60-85%.

    Args:
        days: Number of days.
        seed: Random seed.

    Returns:
        DataFrame with columns: timestamp, outdoor_temp_c,
        outdoor_humidity_pct, solar_radiation_w_m2, wind_speed_ms,
        is_raining.
    """
    rng = np.random.default_rng(seed)
    intervals_per_day = 96  # 15-min intervals
    n = days * intervals_per_day

    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    timestamps = pd.date_range(start=start, periods=n, freq="15min")

    hours = (timestamps.hour + timestamps.minute / 60.0).to_numpy()

    # --- Day-to-day base temperature variation (random walk) ---
    daily_base = np.zeros(days)
    daily_base[0] = 13.0  # March average in Aveiro
    for d in range(1, days):
        daily_base[d] = daily_base[d - 1] + rng.normal(0, 0.8)
        daily_base[d] = np.clip(daily_base[d], 10.0, 16.0)

    # Expand daily base to 15-min resolution
    day_indices = np.arange(n) // intervals_per_day
    base_temp = daily_base[day_indices]

    # --- Diurnal cycle: coldest ~5am, warmest ~15h (3pm) ---
    diurnal_amplitude = 5.0 + rng.normal(0, 0.3, n)
    diurnal = -np.cos(2 * np.pi * (hours - 5) / 24) * diurnal_amplitude / 2
    outdoor_temp = base_temp + diurnal + rng.normal(0, 0.3, n)
    outdoor_temp = np.clip(outdoor_temp, 4.0, 22.0)

    # --- Rain events: ~6 rainy days in 30, multi-hour blocks ---
    is_raining = np.zeros(n, dtype=bool)
    rain_days = rng.choice(days, size=min(6, days), replace=False)
    for rd in rain_days:
        start_interval = rd * intervals_per_day + rng.integers(0, 48)
        duration = rng.integers(16, 48)  # 4-12 hours
        end_interval = min(start_interval + duration, n)
        is_raining[start_interval:end_interval] = True

    # Rain cools temperature slightly
    outdoor_temp[is_raining] -= rng.uniform(1.0, 3.0, is_raining.sum())

    # --- Humidity: anti-correlated with temp, higher at night/rain ---
    temp_normalized = (outdoor_temp - outdoor_temp.min()) / (
        outdoor_temp.max() - outdoor_temp.min() + 1e-6
    )
    outdoor_humidity = 85.0 - 25.0 * temp_normalized + rng.normal(0, 3, n)
    outdoor_humidity[is_raining] += rng.uniform(5, 15, is_raining.sum())
    outdoor_humidity = np.clip(outdoor_humidity, 55.0, 95.0)

    # --- Solar radiation: 0 at night, peak ~600 W/m² midday ---
    sunrise, sunset = 7.0, 19.0  # March in Aveiro approximate
    solar = np.zeros(n)
    daytime = (hours >= sunrise) & (hours <= sunset)
    solar_phase = np.pi * (hours[daytime] - sunrise) / (sunset - sunrise)
    peak_radiation = 600.0 + rng.normal(0, 50, daytime.sum())
    solar[daytime] = np.sin(solar_phase) * peak_radiation
    # Cloud cover reduces solar (rain = heavy cloud)
    cloud_factor = np.ones(n)
    cloud_factor[is_raining] = rng.uniform(0.1, 0.3, is_raining.sum())
    # Random partial cloud on some non-rain intervals
    partial_cloud = rng.random(n) < 0.2
    cloud_factor[partial_cloud & ~is_raining] = rng.uniform(
        0.5, 0.8, (partial_cloud & ~is_raining).sum()
    )
    solar *= cloud_factor
    solar = np.clip(solar, 0, 900)

    # --- Wind speed: 10-25 km/h base, afternoon gusts ---
    wind_base = 15.0 + rng.normal(0, 3, n)
    # Afternoon (12-18h) is windier
    afternoon = (hours >= 12) & (hours <= 18)
    wind_base[afternoon] += rng.uniform(2, 8, afternoon.sum())
    wind_base[is_raining] += rng.uniform(3, 10, is_raining.sum())
    wind_kmh = np.clip(wind_base, 5.0, 40.0)
    wind_ms = wind_kmh / 3.6  # Convert to m/s

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "outdoor_temp_c": np.round(outdoor_temp, 1),
            "outdoor_humidity_pct": np.round(outdoor_humidity, 1),
            "solar_radiation_w_m2": np.round(solar, 0),
            "wind_speed_ms": np.round(wind_ms, 1),
            "is_raining": is_raining,
        }
    )


def generate_shift_schedule(
    days: int = 30,
) -> pd.DataFrame:
    """Generate shift schedule markers.

    Portuguese factory shifts: 6h-14h morning, 14h-22h afternoon.

    Args:
        days: Number of days.

    Returns:
        DataFrame with columns: timestamp, shift, is_business_hours,
        is_weekend.
    """
    n = days * 96
    end = pd.Timestamp.now().normalize()
    start = end - pd.Timedelta(days=days)
    timestamps = pd.date_range(start=start, periods=n, freq="15min")

    hours = timestamps.hour
    dow = timestamps.dayofweek  # 0=Monday, 6=Sunday

    shift = np.where(
        (hours >= 6) & (hours < 14),
        "morning",
        np.where(
            (hours >= 14) & (hours < 22),
            "afternoon",
            "night",
        ),
    )

    is_business_hours = (hours >= 6) & (hours < 22)
    is_weekend = dow >= 5

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "shift": shift,
            "is_business_hours": is_business_hours,
            "is_weekend": is_weekend,
        }
    )


def generate_holidays(year: int = 2026) -> list[date]:
    """Return Portuguese public holidays for a given year.

    Args:
        year: Calendar year.

    Returns:
        List of holiday dates.
    """
    # Fixed Portuguese public holidays
    holidays = [
        date(year, 1, 1),  # Ano Novo
        date(year, 4, 25),  # Dia da Liberdade
        date(year, 5, 1),  # Dia do Trabalhador
        date(year, 6, 10),  # Dia de Portugal
        date(year, 8, 15),  # Assunção de Nossa Senhora
        date(year, 10, 5),  # Implantação da República
        date(year, 11, 1),  # Todos os Santos
        date(year, 12, 1),  # Restauração da Independência
        date(year, 12, 8),  # Imaculada Conceição
        date(year, 12, 25),  # Natal
    ]

    # Easter-dependent holidays for 2026
    # Easter 2026 is April 5
    if year == 2026:
        easter = date(2026, 4, 5)
    else:
        easter = _compute_easter(year)

    holidays.append(easter - timedelta(days=47))  # Carnaval (not official)
    holidays.append(easter - timedelta(days=2))  # Sexta-feira Santa
    holidays.append(easter)  # Domingo de Páscoa
    holidays.append(easter + timedelta(days=60))  # Corpo de Deus

    return sorted(holidays)


def _compute_easter(year: int) -> date:
    """Compute Easter Sunday using the anonymous Gregorian algorithm.

    Args:
        year: Calendar year.

    Returns:
        Date of Easter Sunday.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_val = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_val) // 451
    month, day = divmod(h + l_val - 7 * m + 114, 31)
    return date(year, month, day + 1)
