"""AFI (Architecture of Freedom Intelligence) tunable parameters.

Centralizes all configurable constants for the AFI engine:
financial rates, formula weights, sensor quality multipliers,
and risk parameters. Adjustable via the Deployment admin panel.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AFIConfig(BaseModel):
    """Tunable configuration for the AFI engine."""

    # ── Financial Parameters ──────────────────────
    cost_per_kwh: float = Field(default=0.15, description="€/kWh (Portugal avg)")
    avg_hourly_wage: float = Field(default=12.0, description="€/hr average worker wage")
    impact_factor: float = Field(
        default=0.15, description="Productivity loss factor per comfort deviation unit"
    )
    hvac_efficiency: float = Field(
        default=0.85, description="HVAC COP (coefficient of performance)"
    )
    air_specific_heat: float = Field(default=1.005, description="kJ/(kg·K) for dry air")
    air_density: float = Field(default=1.225, description="kg/m³ at sea level")

    # ── Risk Parameters ───────────────────────────
    asset_value_eur: float = Field(
        default=2_000_000.0, description="Building asset value (€)"
    )
    human_life_value_proxy: float = Field(
        default=500_000.0, description="Statistical value of life proxy (€)"
    )
    base_fire_probability: float = Field(
        default=0.0001, description="Base daily fire probability per zone"
    )

    # ── Distortion Weights (w_k) ──────────────────
    w_temperature: float = Field(
        default=0.30, description="Weight for temperature barrier"
    )
    w_co2: float = Field(default=0.25, description="Weight for CO2 barrier")
    w_crowding: float = Field(
        default=0.25, description="Weight for overcrowding barrier"
    )
    w_blocked_exit: float = Field(
        default=0.20, description="Weight for blocked exit barrier"
    )

    # ── Distortion Interactions (gamma_jk) ────────
    gamma_fire_exit: float = Field(
        default=2.0, description="Synergy multiplier: fire + blocked exit interaction"
    )
    gamma_co2_crowd: float = Field(
        default=0.5, description="Synergy multiplier: CO2 + crowding interaction"
    )

    # ── Stigmergy Parameters ─────────────────────
    evaporation_rate: float = Field(
        default=0.1, description="ρ: pheromone evaporation rate (0-1)"
    )
    deposit_rate: float = Field(default=0.5, description="η: pheromone deposit rate")

    # ── Sensor Quality → Predictive Depth (T) ────
    sensor_depth_cheap_iot: float = Field(
        default=1.0, description="Predictive depth (hours) for cheap IoT"
    )
    sensor_depth_matter: float = Field(
        default=4.0, description="Predictive depth (hours) for Matter"
    )
    sensor_depth_ai_vision: float = Field(
        default=8.0, description="Predictive depth (hours) for AI Vision"
    )

    # ── Comfort Reference Points ─────────────────
    optimal_temperature_c: float = Field(
        default=22.0, description="Reference optimal temperature (°C)"
    )
    optimal_co2_ppm: float = Field(
        default=600.0, description="Reference optimal CO2 (ppm)"
    )
    ceiling_height_m: float = Field(
        default=3.0, description="Default room ceiling height (m)"
    )


# Module-level default instance
DEFAULT_AFI_CONFIG = AFIConfig()
