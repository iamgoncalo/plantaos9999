"""Pydantic models for the AFI rule-based system.

All models are deterministic and serializable.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class Signal(BaseModel):
    """A sensor or derived signal from a zone."""

    zone_id: str
    metric: str  # "temperature_c", "co2_ppm", "occupancy", "energy_kwh"
    value: float
    timestamp: str = ""
    confidence: float = 1.0


class Constraint(BaseModel):
    """A boundary or limit that the system enforces."""

    metric: str
    min_value: float | None = None
    max_value: float | None = None
    weight: float = 1.0
    label: str = ""


class Agent(BaseModel):
    """A virtual agent representing a system concern."""

    id: str
    name: str
    domain: str  # "comfort", "energy", "safety", "utilization"
    priority: float = 1.0
    constraints: list[Constraint] = Field(default_factory=list)


class Action(BaseModel):
    """A proposed action from an agent."""

    agent_id: str
    zone_id: str
    action_type: str  # "adjust_hvac", "alert", "recommend_move", "reduce_lighting"
    description: str
    priority: float = 1.0
    estimated_impact: float = 0.0  # -100 to +100 impact score
    parameters: dict = Field(default_factory=dict)


class Outcome(BaseModel):
    """The evaluated result of a set of actions."""

    zone_id: str
    actions: list[Action] = Field(default_factory=list)
    net_comfort_delta: float = 0.0
    net_energy_delta: float = 0.0
    net_cost_delta: float = 0.0
    confidence: float = 1.0
