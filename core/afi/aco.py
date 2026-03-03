"""Ant Colony Optimization for building flow routing.

Uses pheromone-based exploration on the zone adjacency graph to find
optimal people flow routes that minimize congestion and maximize comfort.
Integrates with the existing stigmergy model in afi_engine.py.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field


class ACOConfig(BaseModel):
    """ACO hyperparameters."""

    n_ants: int = 20
    max_iter: int = 30
    alpha: float = 1.0  # pheromone importance
    beta: float = 2.0  # heuristic importance
    rho: float = 0.1  # evaporation rate
    Q: float = 100.0  # pheromone deposit constant
    seed: int = 42


class Route(BaseModel):
    """A recommended route through the building."""

    path: list[str] = Field(default_factory=list, description="Ordered zone IDs")
    cost: float = 0.0
    pheromone_strength: float = 0.0


class ACOResult(BaseModel):
    """Result of ACO optimization."""

    best_route: Route = Field(default_factory=Route)
    all_routes: list[Route] = Field(default_factory=list)
    pheromone_matrix: dict[str, float] = Field(default_factory=dict)
    iterations_run: int = 0


# Initial pheromone level on all edges
_INITIAL_PHEROMONE: float = 1.0

# Minimum pheromone to prevent starvation of any edge
_MIN_PHEROMONE: float = 0.01


def _edge_key(a: str, b: str) -> str:
    """Create a canonical edge key for a pair of zones.

    Args:
        a: First zone ID.
        b: Second zone ID.

    Returns:
        Edge key string in format "zone1->zone2" (alphabetically ordered).
    """
    if a <= b:
        return f"{a}->{b}"
    return f"{b}->{a}"


def _construct_path(
    adjacency: dict[str, list[str]],
    source: str,
    target: str,
    pheromone: dict[str, float],
    edge_costs: dict[str, float],
    alpha: float,
    beta: float,
    rng: np.random.Generator,
) -> list[str] | None:
    """Construct a single ant's path from source to target.

    Uses probabilistic selection based on pheromone and heuristic:
        P(j) = [tau_j^alpha * eta_j^beta] / sum_k [tau_k^alpha * eta_k^beta]

    where eta_j = 1/cost_j is the heuristic desirability.

    Args:
        adjacency: Zone adjacency dict.
        source: Starting zone ID.
        target: Destination zone ID.
        pheromone: Current pheromone levels per edge.
        edge_costs: Cost per edge (lower is better).
        alpha: Pheromone importance exponent.
        beta: Heuristic importance exponent.
        rng: Numpy random generator.

    Returns:
        List of zone IDs forming the path, or None if no path found.
    """
    path = [source]
    visited: set[str] = {source}
    current = source
    max_steps = len(adjacency) * 2  # prevent infinite loops

    for _ in range(max_steps):
        if current == target:
            return path

        neighbors = adjacency.get(current, [])
        # Filter to unvisited neighbors (allow target even if "visited")
        candidates = [n for n in neighbors if n not in visited or n == target]

        if not candidates:
            return None  # dead end

        # Compute selection probabilities
        n_cand = len(candidates)
        attractiveness = np.zeros(n_cand)

        for i, neighbor in enumerate(candidates):
            ek = _edge_key(current, neighbor)
            tau = pheromone.get(ek, _INITIAL_PHEROMONE)
            cost = edge_costs.get(ek, 1.0)
            eta = 1.0 / max(cost, 0.01)  # heuristic: inverse cost
            attractiveness[i] = (tau**alpha) * (eta**beta)

        total = attractiveness.sum()
        if total <= 0.0:
            # Uniform fallback when all attractiveness is zero
            probabilities = np.ones(n_cand) / n_cand
        else:
            probabilities = attractiveness / total

        # Roulette-wheel selection
        chosen_idx = int(rng.choice(n_cand, p=probabilities))
        chosen = candidates[chosen_idx]

        path.append(chosen)
        visited.add(chosen)
        current = chosen

    return None  # exceeded max steps


def _compute_path_cost(
    path: list[str],
    edge_costs: dict[str, float],
) -> float:
    """Sum edge costs along a path.

    Args:
        path: Ordered list of zone IDs.
        edge_costs: Cost per edge.

    Returns:
        Total path cost.
    """
    total = 0.0
    for i in range(len(path) - 1):
        ek = _edge_key(path[i], path[i + 1])
        total += edge_costs.get(ek, 1.0)
    return total


def aco_optimize(
    adjacency: dict[str, list[str]],
    source: str,
    targets: list[str],
    edge_costs: dict[str, float] | None = None,
    config: ACOConfig | None = None,
) -> ACOResult:
    """Run ACO to find optimal routes from source to targets.

    Path probability: P(j) = [tau_j^alpha * eta_j^beta] / sum_k [tau_k^alpha * eta_k^beta]
    Pheromone update: tau_j = (1-rho) * tau_j + sum_ants delta_tau_j

    Args:
        adjacency: Zone adjacency dict (zone_id -> list of neighbor_ids).
        source: Starting zone ID.
        targets: List of target zone IDs.
        edge_costs: Optional dict of "zone1->zone2" -> cost. Default: uniform.
        config: ACO config override.

    Returns:
        ACOResult with best route and pheromone state.
    """
    cfg = config or ACOConfig()
    rng = np.random.default_rng(cfg.seed)

    # Build default uniform edge costs if not provided
    if edge_costs is None:
        edge_costs = {}
        for zone_id, neighbors in adjacency.items():
            for nbr in neighbors:
                ek = _edge_key(zone_id, nbr)
                if ek not in edge_costs:
                    edge_costs[ek] = 1.0

    # Initialize pheromone on all edges
    pheromone: dict[str, float] = {}
    for zone_id, neighbors in adjacency.items():
        for nbr in neighbors:
            ek = _edge_key(zone_id, nbr)
            if ek not in pheromone:
                pheromone[ek] = _INITIAL_PHEROMONE

    best_route = Route()
    best_cost = float("inf")
    all_routes: list[Route] = []

    for iteration in range(cfg.max_iter):
        iteration_routes: list[tuple[list[str], float]] = []

        # Each ant constructs a path to the closest reachable target
        for _ in range(cfg.n_ants):
            best_ant_path: list[str] | None = None
            best_ant_cost = float("inf")

            for target in targets:
                path = _construct_path(
                    adjacency,
                    source,
                    target,
                    pheromone,
                    edge_costs,
                    cfg.alpha,
                    cfg.beta,
                    rng,
                )
                if path is not None:
                    cost = _compute_path_cost(path, edge_costs)
                    if cost < best_ant_cost:
                        best_ant_cost = cost
                        best_ant_path = path

            if best_ant_path is not None:
                iteration_routes.append((best_ant_path, best_ant_cost))

                # Track global best
                if best_ant_cost < best_cost:
                    best_cost = best_ant_cost
                    avg_pheromone = (
                        np.mean(
                            [
                                pheromone.get(
                                    _edge_key(best_ant_path[i], best_ant_path[i + 1]),
                                    _INITIAL_PHEROMONE,
                                )
                                for i in range(len(best_ant_path) - 1)
                            ]
                        )
                        if len(best_ant_path) > 1
                        else 0.0
                    )
                    best_route = Route(
                        path=best_ant_path,
                        cost=round(best_ant_cost, 4),
                        pheromone_strength=round(float(avg_pheromone), 4),
                    )

        # Pheromone evaporation: tau = (1-rho) * tau
        for ek in pheromone:
            pheromone[ek] = max(
                _MIN_PHEROMONE,
                (1.0 - cfg.rho) * pheromone[ek],
            )

        # Pheromone deposit: ants deposit Q/cost on their path edges
        for path, cost in iteration_routes:
            if cost > 0:
                deposit = cfg.Q / cost
            else:
                deposit = cfg.Q
            for i in range(len(path) - 1):
                ek = _edge_key(path[i], path[i + 1])
                pheromone[ek] = pheromone.get(ek, _MIN_PHEROMONE) + deposit

    # Collect unique routes from last iteration for reporting
    seen_paths: set[tuple[str, ...]] = set()
    for path, cost in iteration_routes:
        path_key = tuple(path)
        if path_key not in seen_paths:
            seen_paths.add(path_key)
            avg_ph = (
                np.mean(
                    [
                        pheromone.get(
                            _edge_key(path[i], path[i + 1]),
                            _MIN_PHEROMONE,
                        )
                        for i in range(len(path) - 1)
                    ]
                )
                if len(path) > 1
                else 0.0
            )
            all_routes.append(
                Route(
                    path=path,
                    cost=round(cost, 4),
                    pheromone_strength=round(float(avg_ph), 4),
                )
            )

    all_routes.sort(key=lambda r: r.cost)

    return ACOResult(
        best_route=best_route,
        all_routes=all_routes,
        pheromone_matrix={k: round(v, 4) for k, v in pheromone.items()},
        iterations_run=cfg.max_iter,
    )


def recommend_flow_routes(
    adjacency: dict[str, list[str]],
    zone_occupancy: dict[str, float],
    zone_capacity: dict[str, int],
    source_zones: list[str],
    target_zones: list[str],
    config: ACOConfig | None = None,
) -> list[Route]:
    """Recommend optimal flow routes based on current congestion.

    Edge costs are computed from congestion: cost = 1 + (occ/cap)^2.
    Higher occupancy relative to capacity makes traversal more expensive,
    steering ants toward less congested paths.

    Args:
        adjacency: Zone adjacency dict.
        zone_occupancy: Current occupancy per zone.
        zone_capacity: Max capacity per zone.
        source_zones: Where people are coming from.
        target_zones: Where people want to go.
        config: ACO config.

    Returns:
        List of Route recommendations sorted by cost (lowest first).
    """
    # Compute congestion-based edge costs
    edge_costs: dict[str, float] = {}
    for zone_id, neighbors in adjacency.items():
        for nbr in neighbors:
            ek = _edge_key(zone_id, nbr)
            if ek not in edge_costs:
                # Cost is average congestion pressure of both endpoints
                occ_a = zone_occupancy.get(zone_id, 0.0)
                cap_a = max(zone_capacity.get(zone_id, 1), 1)
                occ_b = zone_occupancy.get(nbr, 0.0)
                cap_b = max(zone_capacity.get(nbr, 1), 1)

                ratio_a = occ_a / cap_a
                ratio_b = occ_b / cap_b
                avg_ratio = (ratio_a + ratio_b) / 2.0

                # cost = 1 + (occ/cap)^2
                edge_costs[ek] = 1.0 + avg_ratio**2

    # Run ACO for each source-target pair and collect all routes
    all_routes: list[Route] = []
    seen_paths: set[tuple[str, ...]] = set()

    for source in source_zones:
        if source not in adjacency:
            continue

        reachable_targets = [t for t in target_zones if t in adjacency]
        if not reachable_targets:
            continue

        result = aco_optimize(
            adjacency=adjacency,
            source=source,
            targets=reachable_targets,
            edge_costs=edge_costs,
            config=config,
        )

        # Collect best route and unique alternatives
        for route in result.all_routes:
            path_key = tuple(route.path)
            if path_key not in seen_paths and len(route.path) > 1:
                seen_paths.add(path_key)
                all_routes.append(route)

    all_routes.sort(key=lambda r: r.cost)
    return all_routes
