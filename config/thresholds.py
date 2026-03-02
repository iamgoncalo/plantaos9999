"""Operational thresholds for comfort, energy, and safety.

Defines realistic comfort bands based on ISO 7730 / ASHRAE 55 standards,
energy consumption limits per zone type, and safety rules that trigger
immediate alerts. Used by anomaly detection and Freedom Index modules.
"""

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════
# Comfort Band Models
# ═══════════════════════════════════════════════

class ComfortRange(BaseModel):
    """Defines acceptable range for a comfort metric."""

    metric: str = Field(description="Metric name (e.g., 'temperature')")
    unit: str = Field(description="Measurement unit")
    min_optimal: float = Field(description="Lower bound of optimal range")
    max_optimal: float = Field(description="Upper bound of optimal range")
    min_acceptable: float = Field(description="Lower bound before warning")
    max_acceptable: float = Field(description="Upper bound before warning")
    min_critical: float = Field(description="Lower bound for critical alert")
    max_critical: float = Field(description="Upper bound for critical alert")


class EnergyLimit(BaseModel):
    """Energy consumption threshold per zone type."""

    zone_type: str = Field(description="Zone type this applies to")
    max_kwh_per_m2_day: float = Field(description="Maximum daily kWh per m²")
    warning_factor: float = Field(default=0.8, description="Warning at this fraction of max")
    critical_factor: float = Field(default=1.2, description="Critical at this multiple of max")


class SafetyRule(BaseModel):
    """Safety threshold that triggers immediate alerts."""

    name: str = Field(description="Rule identifier")
    description: str = Field(description="Human-readable description")
    metric: str = Field(description="Metric being monitored")
    threshold: float = Field(description="Trigger value")
    comparison: str = Field(description="Operator: 'gt', 'lt', 'gte', 'lte'")
    severity: str = Field(description="Alert severity: 'warning', 'critical', 'emergency'")


# ═══════════════════════════════════════════════
# Comfort Bands
# ═══════════════════════════════════════════════

TEMPERATURE = ComfortRange(
    metric="temperature",
    unit="°C",
    min_optimal=20.0,
    max_optimal=24.0,
    min_acceptable=18.0,
    max_acceptable=26.0,
    min_critical=15.0,
    max_critical=30.0,
)

HUMIDITY = ComfortRange(
    metric="humidity",
    unit="%RH",
    min_optimal=40.0,
    max_optimal=60.0,
    min_acceptable=30.0,
    max_acceptable=70.0,
    min_critical=20.0,
    max_critical=80.0,
)

CO2 = ComfortRange(
    metric="co2",
    unit="ppm",
    min_optimal=400.0,
    max_optimal=800.0,
    min_acceptable=350.0,
    max_acceptable=1000.0,
    min_critical=300.0,
    max_critical=1500.0,
)

ILLUMINANCE = ComfortRange(
    metric="illuminance",
    unit="lux",
    min_optimal=300.0,
    max_optimal=500.0,
    min_acceptable=200.0,
    max_acceptable=750.0,
    min_critical=100.0,
    max_critical=1000.0,
)

NOISE = ComfortRange(
    metric="noise",
    unit="dBA",
    min_optimal=30.0,
    max_optimal=45.0,
    min_acceptable=25.0,
    max_acceptable=55.0,
    min_critical=20.0,
    max_critical=70.0,
)

COMFORT_BANDS: dict[str, ComfortRange] = {
    "temperature": TEMPERATURE,
    "humidity": HUMIDITY,
    "co2": CO2,
    "illuminance": ILLUMINANCE,
    "noise": NOISE,
}

# Corridor-specific illuminance (lower requirements)
ILLUMINANCE_CORRIDOR = ComfortRange(
    metric="illuminance_corridor",
    unit="lux",
    min_optimal=100.0,
    max_optimal=300.0,
    min_acceptable=50.0,
    max_acceptable=400.0,
    min_critical=20.0,
    max_critical=500.0,
)

# Detailed work illuminance (higher requirements)
ILLUMINANCE_DETAILED = ComfortRange(
    metric="illuminance_detailed",
    unit="lux",
    min_optimal=500.0,
    max_optimal=750.0,
    min_acceptable=300.0,
    max_acceptable=1000.0,
    min_critical=200.0,
    max_critical=1500.0,
)


# ═══════════════════════════════════════════════
# Energy Limits (kWh per m² per day)
# ═══════════════════════════════════════════════

ENERGY_LIMITS: dict[str, EnergyLimit] = {
    "training": EnergyLimit(zone_type="training", max_kwh_per_m2_day=0.15),
    "meeting": EnergyLimit(zone_type="meeting", max_kwh_per_m2_day=0.12),
    "office": EnergyLimit(zone_type="office", max_kwh_per_m2_day=0.15),
    "social": EnergyLimit(zone_type="social", max_kwh_per_m2_day=0.10),
    "circulation": EnergyLimit(zone_type="circulation", max_kwh_per_m2_day=0.05),
    "storage": EnergyLimit(zone_type="storage", max_kwh_per_m2_day=0.03),
    "sanitary": EnergyLimit(zone_type="sanitary", max_kwh_per_m2_day=0.08),
    "library": EnergyLimit(zone_type="library", max_kwh_per_m2_day=0.10),
    "it_lab": EnergyLimit(zone_type="it_lab", max_kwh_per_m2_day=0.25),
    "auditorium": EnergyLimit(zone_type="auditorium", max_kwh_per_m2_day=0.12),
    "multipurpose": EnergyLimit(zone_type="multipurpose", max_kwh_per_m2_day=0.15),
    "production": EnergyLimit(zone_type="production", max_kwh_per_m2_day=0.20),
    "dojo": EnergyLimit(zone_type="dojo", max_kwh_per_m2_day=0.12),
    "archive": EnergyLimit(zone_type="archive", max_kwh_per_m2_day=0.03),
    "reception": EnergyLimit(zone_type="reception", max_kwh_per_m2_day=0.08),
}

# Energy breakdown targets (% of total)
ENERGY_BREAKDOWN = {
    "hvac": 0.60,
    "lighting": 0.20,
    "equipment": 0.15,
    "other": 0.05,
}


# ═══════════════════════════════════════════════
# Safety Rules
# ═══════════════════════════════════════════════

SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        name="co2_emergency",
        description="CO2 levels dangerously high — possible ventilation failure",
        metric="co2",
        threshold=1500.0,
        comparison="gt",
        severity="emergency",
    ),
    SafetyRule(
        name="co2_warning",
        description="CO2 levels above acceptable range",
        metric="co2",
        threshold=1000.0,
        comparison="gt",
        severity="warning",
    ),
    SafetyRule(
        name="temperature_high",
        description="Temperature exceeds safe working conditions",
        metric="temperature",
        threshold=30.0,
        comparison="gt",
        severity="critical",
    ),
    SafetyRule(
        name="temperature_low",
        description="Temperature too low for occupancy",
        metric="temperature",
        threshold=15.0,
        comparison="lt",
        severity="critical",
    ),
    SafetyRule(
        name="humidity_high",
        description="Excessive humidity — mold and condensation risk",
        metric="humidity",
        threshold=80.0,
        comparison="gt",
        severity="warning",
    ),
    SafetyRule(
        name="humidity_low",
        description="Very low humidity — respiratory discomfort risk",
        metric="humidity",
        threshold=20.0,
        comparison="lt",
        severity="warning",
    ),
    SafetyRule(
        name="overcrowding",
        description="Zone occupancy exceeds safe capacity",
        metric="occupancy_ratio",
        threshold=1.0,
        comparison="gt",
        severity="critical",
    ),
    SafetyRule(
        name="energy_spike",
        description="Sudden energy consumption spike detected",
        metric="energy_delta_pct",
        threshold=200.0,
        comparison="gt",
        severity="warning",
    ),
]


# ═══════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════

def get_comfort_band(metric: str) -> ComfortRange | None:
    """Look up comfort band by metric name.

    Args:
        metric: The metric name (e.g., 'temperature', 'co2').

    Returns:
        ComfortRange model or None if not found.
    """
    return COMFORT_BANDS.get(metric)


def get_energy_limit(zone_type: str) -> EnergyLimit | None:
    """Look up energy limit by zone type.

    Args:
        zone_type: The zone type string.

    Returns:
        EnergyLimit model or None if not found.
    """
    return ENERGY_LIMITS.get(zone_type)


def evaluate_comfort(metric: str, value: float) -> str:
    """Evaluate a comfort metric value against thresholds.

    Args:
        metric: The metric name.
        value: The measured value.

    Returns:
        Status string: 'optimal', 'acceptable', 'warning', or 'critical'.
    """
    band = COMFORT_BANDS.get(metric)
    if band is None:
        return "unknown"
    if band.min_optimal <= value <= band.max_optimal:
        return "optimal"
    if band.min_acceptable <= value <= band.max_acceptable:
        return "acceptable"
    if value < band.min_critical or value > band.max_critical:
        return "critical"
    return "warning"
