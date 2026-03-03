"""Multi-agent proposal synthesis.

Takes zone state and constraints, generates ranked action proposals.
Deterministic: same inputs always produce same outputs.
"""

from __future__ import annotations

from core.afi.models import Action, Agent, Constraint, Signal


# Pre-defined system agents
SYSTEM_AGENTS: list[Agent] = [
    Agent(
        id="comfort_agent",
        name="Comfort Guardian",
        domain="comfort",
        priority=1.0,
        constraints=[
            Constraint(metric="temperature_c", min_value=20.0, max_value=24.0),
            Constraint(metric="co2_ppm", max_value=1000.0),
            Constraint(metric="humidity_pct", min_value=40.0, max_value=60.0),
        ],
    ),
    Agent(
        id="energy_agent",
        name="Energy Optimizer",
        domain="energy",
        priority=0.8,
        constraints=[
            Constraint(
                metric="energy_kwh", max_value=5.0, label="Max zone energy/interval"
            ),
        ],
    ),
    Agent(
        id="safety_agent",
        name="Safety Monitor",
        domain="safety",
        priority=1.5,
        constraints=[
            Constraint(metric="co2_ppm", max_value=1500.0, label="CO₂ safety limit"),
            Constraint(
                metric="temperature_c", max_value=30.0, label="Heat safety limit"
            ),
        ],
    ),
    Agent(
        id="utilization_agent",
        name="Space Utilization",
        domain="utilization",
        priority=0.6,
        constraints=[
            Constraint(
                metric="occupancy_ratio", max_value=0.9, label="Overcrowding limit"
            ),
        ],
    ),
]


def synthesize_proposals(
    zone_id: str,
    signals: list[Signal],
    agents: list[Agent] | None = None,
) -> list[Action]:
    """Generate ranked action proposals from all agents for a zone.

    Each agent evaluates the signals against its constraints and
    proposes actions when violations are detected.

    Args:
        zone_id: Zone to evaluate.
        signals: Current sensor signals for the zone.
        agents: System agents (defaults to SYSTEM_AGENTS).

    Returns:
        List of Action proposals sorted by priority (highest first).
    """
    agents = agents or SYSTEM_AGENTS
    actions: list[Action] = []

    signal_map = {s.metric: s.value for s in signals}

    for agent in agents:
        for constraint in agent.constraints:
            value = signal_map.get(constraint.metric)
            if value is None:
                continue

            # Check constraint violation
            violated = False
            description = ""

            if constraint.max_value is not None and value > constraint.max_value:
                violated = True
                overshoot = value - constraint.max_value
                description = (
                    f"{constraint.metric} at {value:.1f} exceeds limit "
                    f"{constraint.max_value:.1f} by {overshoot:.1f}"
                )
            elif constraint.min_value is not None and value < constraint.min_value:
                violated = True
                undershoot = constraint.min_value - value
                description = (
                    f"{constraint.metric} at {value:.1f} below minimum "
                    f"{constraint.min_value:.1f} by {undershoot:.1f}"
                )

            if violated:
                action_type = _infer_action_type(agent.domain, constraint.metric)
                impact = _estimate_impact(constraint, value)
                actions.append(
                    Action(
                        agent_id=agent.id,
                        zone_id=zone_id,
                        action_type=action_type,
                        description=description,
                        priority=agent.priority * constraint.weight,
                        estimated_impact=impact,
                        parameters={
                            "metric": constraint.metric,
                            "current_value": value,
                            "target_min": constraint.min_value,
                            "target_max": constraint.max_value,
                        },
                    )
                )

    # Sort by priority descending
    actions.sort(key=lambda a: a.priority, reverse=True)
    return actions


def _infer_action_type(domain: str, metric: str) -> str:
    """Map domain + metric to a recommended action type."""
    if domain == "comfort":
        if "temperature" in metric:
            return "adjust_hvac"
        if "co2" in metric:
            return "increase_ventilation"
        if "humidity" in metric:
            return "adjust_hvac"
        return "adjust_environment"
    if domain == "energy":
        return "reduce_consumption"
    if domain == "safety":
        return "alert"
    if domain == "utilization":
        return "recommend_move"
    return "review"


def _estimate_impact(constraint: Constraint, current_value: float) -> float:
    """Estimate the impact score (-100 to +100) of addressing a violation."""
    if constraint.max_value is not None and current_value > constraint.max_value:
        overshoot_pct = (current_value - constraint.max_value) / max(
            constraint.max_value, 1
        )
        return round(min(overshoot_pct * 100, 100), 1)
    if constraint.min_value is not None and current_value < constraint.min_value:
        undershoot_pct = (constraint.min_value - current_value) / max(
            constraint.min_value, 1
        )
        return round(min(undershoot_pct * 100, 100), 1)
    return 0.0
