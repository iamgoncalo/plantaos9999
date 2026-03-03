"""Sensor catalog with types, costs, and specifications.

Defines available sensor types and deployed sensor tracking models
for the building monitoring system.
"""

from __future__ import annotations

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
    ),
]


def get_sensor_type(type_id: str) -> SensorType | None:
    """Look up a sensor type by ID."""
    for s in SENSOR_CATALOG:
        if s.id == type_id:
            return s
    return None
