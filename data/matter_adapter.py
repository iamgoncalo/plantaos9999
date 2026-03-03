"""Matter protocol adapter — simulated device commissioning and management.

Provides a placeholder adapter for the Matter IoT protocol. In production
this would interface with a real Matter controller; for the MVP it simulates
the commissioning flow and device lifecycle.
"""

from __future__ import annotations

from loguru import logger
from pydantic import BaseModel


class MatterDevice(BaseModel):
    """Represents a Matter-compatible sensor device."""

    device_id: str
    name: str
    vendor: str = "Generic"
    matter_cluster: str = "TemperatureMeasurement"
    commissioned: bool = False
    endpoint: int = 1


class MatterAdapter:
    """Placeholder Matter adapter for MVP. Simulates commissioning flow.

    In production this would communicate with a real Matter fabric
    controller. For the MVP it maintains an in-memory registry of
    commissioned devices and logs all lifecycle events.
    """

    def __init__(self) -> None:
        """Initialize the Matter adapter in simulation mode."""
        self._devices: dict[str, MatterDevice] = {}
        logger.info("Matter adapter initialized (simulation mode)")

    def commission_device(self, device_id: str, zone_id: str) -> MatterDevice:
        """Simulate commissioning a Matter device.

        Args:
            device_id: Unique device identifier.
            zone_id: Zone where the device is being installed.

        Returns:
            The newly commissioned MatterDevice.
        """
        device = MatterDevice(
            device_id=device_id,
            name=f"Matter-{device_id}",
            commissioned=True,
        )
        self._devices[device_id] = device
        logger.info(f"Commissioned Matter device {device_id} in zone {zone_id}")
        return device

    def decommission_device(self, device_id: str) -> bool:
        """Simulate decommissioning a device.

        Args:
            device_id: Device to remove from the fabric.

        Returns:
            True if the device was found and removed, False otherwise.
        """
        if device_id in self._devices:
            del self._devices[device_id]
            logger.info(f"Decommissioned Matter device {device_id}")
            return True
        logger.warning(f"Decommission failed: device {device_id} not found")
        return False

    def get_device_status(self, device_id: str) -> str:
        """Get device commissioning status.

        Args:
            device_id: Device to query.

        Returns:
            Status string: 'commissioned' or 'unknown'.
        """
        device = self._devices.get(device_id)
        if device and device.commissioned:
            return "commissioned"
        return "unknown"

    def list_devices(self) -> list[MatterDevice]:
        """List all commissioned devices.

        Returns:
            List of MatterDevice instances.
        """
        return list(self._devices.values())
