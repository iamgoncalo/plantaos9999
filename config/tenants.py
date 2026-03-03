"""Multi-tenant configuration with Pydantic models.

Defines tenant-specific parameters for scaling building data
across demo deployments.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    """Configuration for a single tenant deployment."""

    id: str = Field(description="Unique tenant identifier")
    name: str = Field(description="Display name")
    building_name: str = Field(description="Building label for header")
    location: str = Field(default="Portugal", description="Geographic location")
    energy_scale: float = Field(default=1.0, description="Energy multiplier for demo")
    occ_scale: float = Field(default=1.0, description="Occupancy multiplier for demo")
    area_m2: float = Field(default=800.0, description="Building area in square meters")
    status: str = Field(default="active", description="Tenant status: active or demo")
    seed: int | None = Field(
        default=None, description="Random seed for data generation"
    )


TENANTS: dict[str, Tenant] = {
    "horse_renault": Tenant(
        id="horse_renault",
        name="HORSE Renault",
        building_name="CFT Aveiro",
        location="Aveiro, Portugal",
        energy_scale=1.0,
        occ_scale=1.0,
        area_m2=800.0,
        status="active",
        seed=42,
    ),
    "airbus_assembly": Tenant(
        id="airbus_assembly",
        name="Airbus Assembly",
        building_name="FAL A320",
        location="Toulouse, France",
        energy_scale=12.5,
        occ_scale=8.0,
        area_m2=15000.0,
        status="demo",
    ),
    "ikea_logistics": Tenant(
        id="ikea_logistics",
        name="IKEA Logistics",
        building_name="DC Almeirim",
        location="Almeirim, Portugal",
        energy_scale=35.0,
        occ_scale=15.0,
        area_m2=42000.0,
        status="demo",
    ),
}


def get_tenant(tenant_id: str) -> Tenant | None:
    """Get tenant configuration by ID.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Tenant model, or None if not found.
    """
    return TENANTS.get(tenant_id)
