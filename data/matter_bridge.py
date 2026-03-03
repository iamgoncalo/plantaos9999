"""Simulated Matter IoT protocol bridge.

Simulates ingestion of sensor data following the Matter IoT standard
(IPv6-based, standardized clusters for Temperature, Occupancy, HVAC, Safety).
Models three tiers of sensors: Cheap IoT, Matter-Compliant, and AI Vision.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field

from config.building import get_monitored_zones
from data.store import store


class SensorType(str, Enum):
    """Sensor quality tier."""

    CHEAP_IOT = "cheap_iot"
    MATTER_COMPLIANT = "matter"
    AI_VISION = "ai_vision"


class MatterCluster(str, Enum):
    """Matter standard cluster types."""

    TEMPERATURE = "temperature_measurement"
    HUMIDITY = "relative_humidity_measurement"
    OCCUPANCY = "occupancy_sensing"
    CO2 = "carbon_dioxide_concentration"
    ILLUMINANCE = "illuminance_measurement"
    HVAC = "thermostat"
    FIRE_SAFETY = "smoke_co_alarm"
    POWER = "electrical_power_measurement"


class MatterDevice(BaseModel):
    """A simulated Matter-compatible IoT sensor device."""

    device_id: str = Field(description="Unique device identifier")
    zone_id: str = Field(description="Zone where device is installed")
    sensor_type: SensorType = Field(description="Quality tier")
    cluster: MatterCluster = Field(description="Matter cluster type")
    endpoint: int = Field(default=1, description="Matter endpoint number")
    last_reading: datetime | None = Field(
        default=None, description="Timestamp of last reading"
    )
    accuracy: float = Field(default=0.9, description="Measurement accuracy (0-1)")

    @property
    def sampling_interval_seconds(self) -> int:
        """Return sampling interval based on sensor type."""
        intervals = {
            SensorType.CHEAP_IOT: 900,  # 15 minutes
            SensorType.MATTER_COMPLIANT: 60,  # 1 minute
            SensorType.AI_VISION: 10,  # 10 seconds
        }
        return intervals.get(self.sensor_type, 900)


class SensorDeployment(BaseModel):
    """Complete sensor deployment for the building."""

    devices: list[MatterDevice] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def zone_sensor_types(self) -> dict[str, str]:
        """Return best sensor type per zone."""
        result: dict[str, str] = {}
        priority = {
            SensorType.AI_VISION: 3,
            SensorType.MATTER_COMPLIANT: 2,
            SensorType.CHEAP_IOT: 1,
        }
        for device in self.devices:
            current = result.get(device.zone_id, SensorType.CHEAP_IOT)
            if priority.get(device.sensor_type, 0) > priority.get(
                SensorType(current), 0
            ):
                result[device.zone_id] = device.sensor_type.value
        return result

    @property
    def total_devices(self) -> int:
        """Return total number of deployed devices."""
        return len(self.devices)

    def devices_by_zone(self, zone_id: str) -> list[MatterDevice]:
        """Return all devices in a specific zone."""
        return [d for d in self.devices if d.zone_id == zone_id]


# ═══════════════════════════════════════════════
# Default Deployment (Cheap IoT Everywhere)
# ═══════════════════════════════════════════════

_CLUSTER_SETS: dict[SensorType, list[MatterCluster]] = {
    SensorType.CHEAP_IOT: [
        MatterCluster.TEMPERATURE,
        MatterCluster.HUMIDITY,
    ],
    SensorType.MATTER_COMPLIANT: [
        MatterCluster.TEMPERATURE,
        MatterCluster.HUMIDITY,
        MatterCluster.CO2,
        MatterCluster.ILLUMINANCE,
        MatterCluster.OCCUPANCY,
        MatterCluster.POWER,
    ],
    SensorType.AI_VISION: [
        MatterCluster.TEMPERATURE,
        MatterCluster.HUMIDITY,
        MatterCluster.CO2,
        MatterCluster.ILLUMINANCE,
        MatterCluster.OCCUPANCY,
        MatterCluster.POWER,
        MatterCluster.FIRE_SAFETY,
        MatterCluster.HVAC,
    ],
}

_ACCURACY: dict[SensorType, float] = {
    SensorType.CHEAP_IOT: 0.85,
    SensorType.MATTER_COMPLIANT: 0.95,
    SensorType.AI_VISION: 0.99,
}


def get_default_deployment() -> SensorDeployment:
    """Generate the default sensor deployment (cheap IoT everywhere).

    Returns:
        SensorDeployment with basic sensors in all monitored zones.
    """
    devices: list[MatterDevice] = []
    for zone in get_monitored_zones():
        for i, cluster in enumerate(_CLUSTER_SETS[SensorType.CHEAP_IOT]):
            devices.append(
                MatterDevice(
                    device_id=f"{zone.id}_cheap_{i}",
                    zone_id=zone.id,
                    sensor_type=SensorType.CHEAP_IOT,
                    cluster=cluster,
                    endpoint=i + 1,
                    accuracy=_ACCURACY[SensorType.CHEAP_IOT],
                )
            )
    logger.debug(
        f"Default deployment: {len(devices)} devices across {len(get_monitored_zones())} zones"
    )
    return SensorDeployment(devices=devices)


def create_upgraded_deployment(
    base: SensorDeployment,
    zone_upgrades: dict[str, SensorType],
) -> SensorDeployment:
    """Create a new deployment with upgraded sensors for specific zones.

    Args:
        base: Current deployment.
        zone_upgrades: Dict zone_id → target SensorType.

    Returns:
        New SensorDeployment with upgraded devices.
    """
    upgraded_zones = set(zone_upgrades.keys())
    # Keep devices from non-upgraded zones
    devices = [d for d in base.devices if d.zone_id not in upgraded_zones]

    # Add new devices for upgraded zones
    for zone_id, new_type in zone_upgrades.items():
        for i, cluster in enumerate(_CLUSTER_SETS.get(new_type, [])):
            devices.append(
                MatterDevice(
                    device_id=f"{zone_id}_{new_type.value}_{i}",
                    zone_id=zone_id,
                    sensor_type=new_type,
                    cluster=cluster,
                    endpoint=i + 1,
                    accuracy=_ACCURACY.get(new_type, 0.9),
                )
            )

    return SensorDeployment(devices=devices)


def simulate_matter_reading(device: MatterDevice) -> dict[str, Any]:
    """Generate a simulated sensor reading from the existing data store.

    Args:
        device: The device to read from.

    Returns:
        Dict with cluster-appropriate measurement values.
    """
    zone_id = device.zone_id
    reading: dict[str, Any] = {
        "device_id": device.device_id,
        "zone_id": zone_id,
        "cluster": device.cluster.value,
        "timestamp": datetime.now().isoformat(),
    }

    if device.cluster == MatterCluster.TEMPERATURE:
        df = store.get_zone_data("comfort", zone_id)
        if df is not None and not df.empty:
            val = df.sort_values("timestamp").iloc[-1].get("temperature_c", 22.0)
            noise = np.random.normal(0, 0.5 * (1 - device.accuracy))
            reading["value"] = round(float(val) + noise, 2)
            reading["unit"] = "°C"

    elif device.cluster == MatterCluster.CO2:
        df = store.get_zone_data("comfort", zone_id)
        if df is not None and not df.empty:
            val = df.sort_values("timestamp").iloc[-1].get("co2_ppm", 450)
            noise = np.random.normal(0, 20 * (1 - device.accuracy))
            reading["value"] = round(max(300, float(val) + noise), 0)
            reading["unit"] = "ppm"

    elif device.cluster == MatterCluster.OCCUPANCY:
        df = store.get_zone_data("occupancy", zone_id)
        if df is not None and not df.empty:
            val = df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
            reading["value"] = int(val)
            reading["occupied"] = int(val) > 0

    elif device.cluster == MatterCluster.POWER:
        df = store.get_zone_data("energy", zone_id)
        if df is not None and not df.empty:
            val = df.sort_values("timestamp").iloc[-1].get("total_kwh", 0)
            reading["value"] = round(float(val), 4)
            reading["unit"] = "kWh"

    elif device.cluster == MatterCluster.FIRE_SAFETY:
        reading["smoke_detected"] = False
        reading["co_detected"] = False
        reading["battery_pct"] = 95

    return reading


def get_sensor_quality_multiplier(sensor_type: str) -> float:
    """Return Perception depth (T) multiplier for a sensor type.

    Args:
        sensor_type: Sensor type string.

    Returns:
        Predictive depth multiplier (1.0 for cheap, 4.0 for matter, 8.0 for AI).
    """
    multipliers = {
        "cheap_iot": 1.0,
        "matter": 4.0,
        "ai_vision": 8.0,
    }
    return multipliers.get(sensor_type, 1.0)


def compute_sensor_coverage(deployment: SensorDeployment) -> dict[str, float]:
    """Compute coverage percentage per Matter cluster.

    Args:
        deployment: Current sensor deployment.

    Returns:
        Dict cluster_name → coverage fraction (0-1).
    """
    total_zones = len(get_monitored_zones())
    if total_zones == 0:
        return {}

    coverage: dict[str, set[str]] = {}
    for device in deployment.devices:
        cluster_name = device.cluster.value
        if cluster_name not in coverage:
            coverage[cluster_name] = set()
        coverage[cluster_name].add(device.zone_id)

    return {cluster: len(zones) / total_zones for cluster, zones in coverage.items()}


# Module-level default deployment
_default_deployment: SensorDeployment | None = None


def get_current_deployment() -> SensorDeployment:
    """Return the current active sensor deployment (lazy init).

    Returns:
        The active SensorDeployment instance.
    """
    global _default_deployment  # noqa: PLW0603
    if _default_deployment is None:
        _default_deployment = get_default_deployment()
    return _default_deployment


def set_deployment(deployment: SensorDeployment) -> None:
    """Replace the active sensor deployment.

    Args:
        deployment: New deployment to activate.
    """
    global _default_deployment  # noqa: PLW0603
    _default_deployment = deployment
    logger.info(f"Sensor deployment updated: {deployment.total_devices} devices")
