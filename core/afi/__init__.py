"""AFI (Adaptive Freedom Index) internal package.

Provides deterministic rule-based models for zone health scoring,
multi-agent proposal synthesis, and constraint optimization.
All computations are deterministic — same inputs produce same outputs.
"""

from core.afi.models import Action, Agent, Constraint, Outcome, Signal
from core.afi.rules import evaluate_comfort_boundary, evaluate_cost_function
from core.afi.swarm import synthesize_proposals

__all__ = [
    "Action",
    "Agent",
    "Constraint",
    "Outcome",
    "Signal",
    "evaluate_comfort_boundary",
    "evaluate_cost_function",
    "synthesize_proposals",
]
