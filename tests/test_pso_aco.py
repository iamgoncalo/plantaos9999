"""Tests for PSO and ACO optimization modules."""

from __future__ import annotations

from core.afi.aco import ACOConfig, ACOResult, aco_optimize
from core.afi.pso import PSOConfig, PSOResult, pso_optimize


def test_pso_converges_on_quadratic() -> None:
    """PSO finds the minimum of a simple quadratic f(x) = x1² + x2²."""

    def quadratic(x: list[float]) -> float:
        return sum(xi**2 for xi in x)

    result = pso_optimize(
        quadratic,
        bounds=[(-5.0, 5.0), (-5.0, 5.0)],
        config=PSOConfig(n_particles=30, max_iter=100, seed=42),
    )

    assert isinstance(result, PSOResult)
    assert result.best_fitness < 0.1, f"Fitness {result.best_fitness} not near 0"
    assert len(result.best_position) == 2
    for xi in result.best_position:
        assert abs(xi) < 0.5


def test_pso_respects_bounds() -> None:
    """PSO result stays within specified bounds."""

    def offset_quad(x: list[float]) -> float:
        return (x[0] - 3.0) ** 2 + (x[1] + 2.0) ** 2

    result = pso_optimize(
        offset_quad,
        bounds=[(-10.0, 10.0), (-10.0, 10.0)],
        config=PSOConfig(n_particles=20, max_iter=50, seed=42),
    )

    assert -10.0 <= result.best_position[0] <= 10.0
    assert -10.0 <= result.best_position[1] <= 10.0


def test_pso_result_model_fields() -> None:
    """PSOResult has all expected fields."""
    result = PSOResult(
        best_position=[1.0, 2.0],
        best_fitness=0.5,
        iterations_run=10,
        converged=True,
    )
    assert result.converged is True
    assert result.iterations_run == 10


def test_aco_finds_path_in_simple_graph() -> None:
    """ACO finds a path in a simple 4-node graph."""
    adjacency = {
        "A": ["B", "C"],
        "B": ["A", "D"],
        "C": ["A", "D"],
        "D": ["B", "C"],
    }

    result = aco_optimize(
        adjacency=adjacency,
        source="A",
        targets=["D"],
        config=ACOConfig(n_ants=10, max_iter=10, seed=42),
    )

    assert isinstance(result, ACOResult)
    assert result.best_route.path[0] == "A"
    assert result.best_route.path[-1] == "D"
    assert len(result.best_route.path) >= 2


def test_aco_with_edge_costs() -> None:
    """ACO prefers lower-cost edges."""
    adjacency = {
        "A": ["B", "C"],
        "B": ["A", "D"],
        "C": ["A", "D"],
        "D": ["B", "C"],
    }
    # Make A->B->D cheap, A->C->D expensive
    edge_costs = {
        "A->B": 1.0,
        "B->D": 1.0,
        "A->C": 10.0,
        "C->D": 10.0,
    }

    result = aco_optimize(
        adjacency=adjacency,
        source="A",
        targets=["D"],
        edge_costs=edge_costs,
        config=ACOConfig(n_ants=20, max_iter=20, seed=42),
    )

    # The best route should prefer A->B->D
    assert result.best_route.path == ["A", "B", "D"]


def test_aco_unreachable_target() -> None:
    """ACO handles unreachable target gracefully."""
    adjacency = {
        "A": ["B"],
        "B": ["A"],
        "C": [],  # isolated
    }

    result = aco_optimize(
        adjacency=adjacency,
        source="A",
        targets=["C"],
        config=ACOConfig(n_ants=5, max_iter=5, seed=42),
    )

    # Should still return a result (possibly empty route)
    assert isinstance(result, ACOResult)


def test_aco_result_model_fields() -> None:
    """ACOResult has all expected fields."""
    result = ACOResult(iterations_run=5)
    assert result.iterations_run == 5
    assert result.best_route.path == []
    assert result.pheromone_matrix == {}
