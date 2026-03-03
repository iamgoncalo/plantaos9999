"""Sensor catalog with types, costs, and specifications.

Defines available sensor types and deployed sensor tracking models
for the building monitoring system.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field


class SensorType(BaseModel):
    """Specification for a sensor type in the catalog."""

    id: str
    name: str
    category: str  # "environmental", "occupancy", "energy", "safety"
    cost_eur: float
    install_cost_eur: float = 0.0
    maintenance_cost_eur_year: float = 0.0
    battery_days: int = 0  # 0 = wired
    sample_rate_s: int = 300
    coverage_radius_m: float = 3.0
    measures: list[str] = Field(default_factory=list)
    description: str = ""
    noise_sigma: float = 0.1
    drift_rate_per_hour: float = 0.0
    packet_loss_prob: float = 0.02


class DeployedSensor(BaseModel):
    """A deployed sensor instance in the building."""

    id: str
    type_id: str
    zone_id: str
    position_x: float = 0.0
    position_y: float = 0.0
    installed_at: str = ""
    health_status: str = "healthy"  # healthy, warning, critical
    battery_pct: float = 100.0
    calibration_due: str = ""
    battery_mah: float = 2000.0
    tx_cost_mah: float = 0.5
    idle_cost_mah: float = 0.01
    firmware_version: str = "1.0.0"
    last_seen_ts: str = ""
    reliability_score: float = 1.0


class SensorReading(BaseModel):
    """A single sensor reading with raw and corrected values."""

    device_id: str
    ts: str  # ISO timestamp
    metric: str
    raw_value: float
    corrected_value: float = 0.0
    quality_flags: list[str] = Field(default_factory=list)


SENSOR_CATALOG: list[SensorType] = [
    SensorType(
        id="temp_hum",
        name="Temp/Humidity",
        category="environmental",
        cost_eur=25.0,
        install_cost_eur=15.0,
        maintenance_cost_eur_year=5.0,
        battery_days=365,
        sample_rate_s=300,
        coverage_radius_m=2.0,
        measures=["temperature", "humidity"],
        description="Basic temperature and humidity sensor",
        noise_sigma=0.2,
        drift_rate_per_hour=0.001,
    ),
    SensorType(
        id="co2_combo",
        name="CO\u2082 + Temp + Humidity",
        category="environmental",
        cost_eur=85.0,
        install_cost_eur=20.0,
        maintenance_cost_eur_year=10.0,
        battery_days=180,
        sample_rate_s=300,
        coverage_radius_m=3.0,
        measures=["temperature", "humidity", "co2"],
        description="Combined air quality sensor",
        noise_sigma=15.0,
        drift_rate_per_hour=0.5,
    ),
    SensorType(
        id="lux_sensor",
        name="Light Level Sensor",
        category="environmental",
        cost_eur=35.0,
        install_cost_eur=10.0,
        maintenance_cost_eur_year=5.0,
        battery_days=730,
        sample_rate_s=60,
        coverage_radius_m=4.0,
        measures=["illuminance"],
        description="Ambient light level measurement",
        noise_sigma=5.0,
        drift_rate_per_hour=0.01,
    ),
    SensorType(
        id="pir_occupancy",
        name="PIR Occupancy",
        category="occupancy",
        cost_eur=45.0,
        install_cost_eur=20.0,
        maintenance_cost_eur_year=5.0,
        battery_days=365,
        sample_rate_s=10,
        coverage_radius_m=4.0,
        measures=["occupancy"],
        description="Passive infrared motion detection",
        noise_sigma=0.0,
        drift_rate_per_hour=0.0,
        packet_loss_prob=0.05,
    ),
    SensorType(
        id="mmwave_occupancy",
        name="mmWave Occupancy",
        category="occupancy",
        cost_eur=180.0,
        install_cost_eur=30.0,
        maintenance_cost_eur_year=10.0,
        battery_days=0,
        sample_rate_s=5,
        coverage_radius_m=5.0,
        measures=["occupancy", "people_count"],
        description="Millimeter wave people counting",
        noise_sigma=0.0,
        drift_rate_per_hour=0.0,
        packet_loss_prob=0.01,
    ),
    SensorType(
        id="door_contact",
        name="Door Contact",
        category="occupancy",
        cost_eur=15.0,
        install_cost_eur=10.0,
        maintenance_cost_eur_year=2.0,
        battery_days=1095,
        sample_rate_s=0,
        coverage_radius_m=0.5,
        measures=["door_state"],
        description="Magnetic door open/close sensor",
        noise_sigma=0.0,
        drift_rate_per_hour=0.0,
        packet_loss_prob=0.03,
    ),
    SensorType(
        id="energy_meter",
        name="Energy Sub-meter",
        category="energy",
        cost_eur=120.0,
        install_cost_eur=50.0,
        maintenance_cost_eur_year=15.0,
        battery_days=0,
        sample_rate_s=60,
        coverage_radius_m=0.0,
        measures=["energy"],
        description="Zone-level energy consumption monitoring",
        noise_sigma=0.05,
        drift_rate_per_hour=0.002,
    ),
    SensorType(
        id="smoke_fire",
        name="Smoke/Fire Detector",
        category="safety",
        cost_eur=55.0,
        install_cost_eur=25.0,
        maintenance_cost_eur_year=10.0,
        battery_days=1825,
        sample_rate_s=5,
        coverage_radius_m=6.0,
        measures=["smoke", "fire"],
        description="Photoelectric smoke and heat detector",
        noise_sigma=0.0,
        drift_rate_per_hour=0.0,
        packet_loss_prob=0.01,
    ),
    SensorType(
        id="noise_sensor",
        name="Noise Level Sensor",
        category="environmental",
        cost_eur=65.0,
        install_cost_eur=15.0,
        maintenance_cost_eur_year=5.0,
        battery_days=365,
        sample_rate_s=60,
        coverage_radius_m=3.0,
        measures=["noise_db"],
        description="Ambient noise level measurement",
        noise_sigma=1.5,
        drift_rate_per_hour=0.05,
    ),
]


def get_sensor_type(type_id: str) -> SensorType | None:
    """Look up a sensor type by ID."""
    for s in SENSOR_CATALOG:
        if s.id == type_id:
            return s
    return None


def apply_sensor_model(
    true_value: float,
    noise_sigma: float = 0.1,
    bias: float = 0.0,
    drift_hours: float = 0.0,
    drift_rate: float = 0.0,
    p_loss: float = 0.02,
    rng: np.random.Generator | None = None,
) -> tuple[float | None, list[str]]:
    """Apply sensor noise model: y(t) = x(t) + b + eps(t) + drift(t).

    Models realistic sensor imperfections including measurement noise,
    fixed bias, time-dependent drift, and packet loss.

    Args:
        true_value: The actual physical value being measured.
        noise_sigma: Standard deviation of Gaussian measurement noise.
        bias: Fixed sensor bias offset.
        drift_hours: Hours since last calibration (for drift calculation).
        drift_rate: Drift rate in units per hour.
        p_loss: Probability of a lost/dropped reading.
        rng: NumPy random generator (created if None).

    Returns:
        Tuple of (measured_value_or_None, quality_flags). None indicates
        a lost packet. quality_flags lists any issues detected.
    """
    if rng is None:
        rng = np.random.default_rng()

    flags: list[str] = []

    # Packet loss check
    if rng.random() < p_loss:
        return None, ["packet_lost"]

    # Gaussian measurement noise
    noise = rng.normal(0, noise_sigma) if noise_sigma > 0 else 0.0

    # Time-dependent drift
    drift = drift_rate * drift_hours

    # Compose measured value
    measured = true_value + bias + noise + drift

    # Flag significant drift
    if abs(drift) > noise_sigma * 3 and noise_sigma > 0:
        flags.append("drift_warning")

    # Flag extreme noise (>3 sigma deviation)
    if abs(noise) > noise_sigma * 3 and noise_sigma > 0:
        flags.append("noise_spike")

    return measured, flags
