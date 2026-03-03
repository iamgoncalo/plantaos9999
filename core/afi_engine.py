"""AFI (Architecture of Freedom Intelligence) engine.

Implements the core mathematical framework for spatial intelligence:
- Perception (P): sensor coverage and predictive depth
- Geometric Distortion (D): log-linear barrier interaction model
- Freedom (F = P / D): the spatial health index
- Swarm Stigmergy: pheromone-based routing optimization
- Financial Bleed: real-time € cost of building inefficiencies
- Risk Assessment: catastrophic event cost estimation
- NetworkX spatial graph for topology analysis and optimal routing

All formulas use numpy/scipy for vectorized computation.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import networkx as nx
import numpy as np
from loguru import logger
from pydantic import BaseModel, Field

from config.afi_config import AFIConfig, DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
from config.thresholds import COMFORT_BANDS
from data.store import store


# ═══════════════════════════════════════════════
# Realistic Financial Caps
# ═══════════════════════════════════════════════
# ~500m² building, €3000/month ÷ 720hrs ≈ €4.17/hr
MAX_BUILDING_BLEED_EUR_HR = 8.0  # generous cap with margin
MAX_ZONE_BLEED_EUR_HR = 3.0  # no single zone exceeds this

# ═══════════════════════════════════════════════
# EMA (Exponential Moving Average) Smoothing
# ═══════════════════════════════════════════════
EMA_ALPHA = 0.3  # Smoothing factor (0.3 = responsive yet stable)
_ema_state: dict[str, dict[str, float]] = {}  # zone_id → {metric: ema_value}


def _ema_smooth(zone_id: str, metric: str, new_value: float) -> float:
    """Apply EMA smoothing to a metric value for smooth data drift.

    EMA(t) = α · X(t) + (1 - α) · EMA(t-1)

    Args:
        zone_id: Zone identifier.
        metric: Metric name (e.g., 'freedom', 'bleed').
        new_value: New raw value.

    Returns:
        Smoothed value.
    """
    if zone_id not in _ema_state:
        _ema_state[zone_id] = {}
    prev = _ema_state[zone_id].get(metric)
    if prev is None:
        _ema_state[zone_id][metric] = new_value
        return new_value
    smoothed = EMA_ALPHA * new_value + (1 - EMA_ALPHA) * prev
    _ema_state[zone_id][metric] = smoothed
    return smoothed


# ═══════════════════════════════════════════════
# Pydantic Result Models
# ═══════════════════════════════════════════════


class PerceptionResult(BaseModel):
    """Result of Perception (P) computation for a zone."""

    zone_id: str
    N: int = Field(description="Distinguishable paths/exits")
    T: float = Field(description="Predictive depth (hours)")
    P: float = Field(description="Perception = log2(N) * T")


class DistortionResult(BaseModel):
    """Result of Geometric Distortion (D) computation for a zone."""

    zone_id: str
    barriers: dict[str, float] = Field(description="d_k barrier values")
    weights: dict[str, float] = Field(description="w_k weight values")
    interactions: dict[str, float] = Field(description="gamma_jk interaction values")
    D: float = Field(description="Distortion = exp(Σ w·ln(d) + Σ γ·ln(d_j)·ln(d_k))")


class FreedomResult(BaseModel):
    """Result of Freedom (F = P / D) computation."""

    zone_id: str
    P: float = Field(description="Perception score")
    D: float = Field(description="Distortion score")
    F: float = Field(description="Freedom = P / D")


class FinancialBleed(BaseModel):
    """Financial cost breakdown for a zone per hour."""

    zone_id: str
    energy_cost_eur_hr: float = 0.0
    open_window_penalty_eur_hr: float = 0.0
    human_capital_loss_eur_hr: float = 0.0
    total_bleed_eur_hr: float = 0.0


class RiskAssessment(BaseModel):
    """Catastrophic risk cost assessment for a zone."""

    zone_id: str
    hazard_probability: float = 0.0
    risk_cost_eur: float = 0.0


class StigmergyState(BaseModel):
    """Pheromone state for swarm routing across zone edges."""

    edges: dict[str, float] = Field(
        default_factory=dict, description="Edge ID → pheromone level"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class ZoneAFI(BaseModel):
    """Complete AFI assessment for a single zone."""

    zone_id: str
    perception: PerceptionResult
    distortion: DistortionResult
    freedom: FreedomResult
    financial: FinancialBleed
    risk: RiskAssessment


class BuildingAFI(BaseModel):
    """Complete AFI assessment for the entire building."""

    timestamp: datetime = Field(default_factory=datetime.now)
    zones: dict[str, ZoneAFI] = Field(default_factory=dict)
    stigmergy: StigmergyState = Field(default_factory=StigmergyState)
    total_financial_bleed_eur_hr: float = 0.0
    avg_freedom: float = 0.0
    total_risk_eur: float = 0.0


# ═══════════════════════════════════════════════
# Zone Adjacency Graph (computed from geometry)
# ═══════════════════════════════════════════════

# Number of exits/adjacent zones per zone (from geometry analysis)
_ZONE_ADJACENCY: dict[str, list[str]] = {
    "p0_multiusos": ["p0_circulacao", "p0_biblioteca"],
    "p0_biblioteca": ["p0_multiusos", "p0_circulacao", "p0_hall"],
    "p0_hall": ["p0_biblioteca", "p0_circulacao", "p0_reuniao"],
    "p0_reuniao": ["p0_hall", "p0_recepcao", "p0_wc"],
    "p0_recepcao": ["p0_reuniao", "p0_arrumo"],
    "p0_arrumo": ["p0_recepcao", "p0_wc"],
    "p0_wc": ["p0_reuniao", "p0_arrumo"],
    "p0_circulacao": [
        "p0_multiusos",
        "p0_biblioteca",
        "p0_hall",
        "p0_auditorio",
        "p0_sala",
        "p0_copa",
        "p0_informatica",
        "p0_formacao1",
        "p0_formacao2",
        "p0_formacao3",
    ],
    "p0_auditorio": ["p0_circulacao"],
    "p0_sala": ["p0_circulacao"],
    "p0_copa": ["p0_circulacao"],
    "p0_informatica": ["p0_circulacao"],
    "p0_formacao1": ["p0_circulacao", "p0_formacao2"],
    "p0_formacao2": ["p0_circulacao", "p0_formacao1", "p0_formacao3"],
    "p0_formacao3": ["p0_circulacao", "p0_formacao2"],
    "p1_dojo": ["p1_circulacao", "p1_arquivo"],
    "p1_arquivo": ["p1_dojo", "p1_circulacao", "p1_sala_a"],
    "p1_sala_a": ["p1_arquivo", "p1_circulacao", "p1_reunioes"],
    "p1_reunioes": ["p1_sala_a", "p1_wc", "p1_arrumos"],
    "p1_circulacao": [
        "p1_dojo",
        "p1_arquivo",
        "p1_sala_a",
        "p1_sala_b",
        "p1_sala_c",
        "p1_sala_d",
        "p1_salagrande",
    ],
    "p1_sala_b": ["p1_circulacao"],
    "p1_sala_c": ["p1_circulacao"],
    "p1_sala_d": ["p1_circulacao"],
    "p1_wc": ["p1_reunioes"],
    "p1_arrumos": ["p1_reunioes"],
    "p1_salagrande": ["p1_circulacao", "p1_salapequena", "p1_arquivo"],
    "p1_salapequena": ["p1_salagrande", "p1_armazem"],
    "p1_armazem": ["p1_salapequena"],
}

# Edge definitions for stigmergy routing
_ZONE_EDGES: list[tuple[str, str]] = []
_seen_edges: set[frozenset[str]] = set()
for _zid, _neighbors in _ZONE_ADJACENCY.items():
    for _n in _neighbors:
        edge_key = frozenset([_zid, _n])
        if edge_key not in _seen_edges:
            _seen_edges.add(edge_key)
            _ZONE_EDGES.append((_zid, _n))


# ═══════════════════════════════════════════════
# NetworkX Spatial Graph
# ═══════════════════════════════════════════════

_SPATIAL_GRAPH: nx.Graph | None = None


def build_spatial_graph() -> nx.Graph:
    """Build a NetworkX graph from zone adjacency data.

    Nodes carry zone metadata (area, capacity, floor).
    Edges carry inverse-capacity weights for shortest-path routing.

    Returns:
        Weighted undirected graph of the building topology.
    """
    global _SPATIAL_GRAPH
    if _SPATIAL_GRAPH is not None:
        return _SPATIAL_GRAPH

    G = nx.Graph()

    for zone_id, neighbors in _ZONE_ADJACENCY.items():
        zone = get_zone_by_id(zone_id)
        area = zone.area_m2 if zone else 40.0
        cap = zone.capacity if zone else 20
        floor_num = 0 if zone_id.startswith("p0") else 1
        G.add_node(
            zone_id,
            area=area,
            capacity=cap,
            floor=floor_num,
            name=zone.name if zone else zone_id,
        )
        for nbr in neighbors:
            if not G.has_edge(zone_id, nbr):
                # Weight: inverse capacity means corridors are cheap to traverse
                nbr_zone = get_zone_by_id(nbr)
                nbr_cap = nbr_zone.capacity if nbr_zone else 20
                weight = 1.0 / max(min(cap, nbr_cap), 1)
                G.add_edge(zone_id, nbr, weight=weight)

    _SPATIAL_GRAPH = G
    return G


def get_shortest_path(
    source: str,
    target: str,
) -> list[str]:
    """Find shortest path between two zones.

    Args:
        source: Source zone ID.
        target: Target zone ID.

    Returns:
        List of zone IDs along the shortest path.
    """
    G = build_spatial_graph()
    try:
        return nx.shortest_path(G, source, target, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def get_evacuation_paths(
    source: str,
    exit_zones: list[str] | None = None,
) -> dict[str, list[str]]:
    """Compute evacuation paths from a zone to all exits.

    Args:
        source: Starting zone ID.
        exit_zones: Optional list of exit zone IDs. Defaults to
            corridors and hall.

    Returns:
        Dict mapping exit zone → shortest path from source.
    """
    if exit_zones is None:
        exit_zones = ["p0_hall", "p0_circulacao", "p1_circulacao"]

    G = build_spatial_graph()
    paths: dict[str, list[str]] = {}
    for exit_zone in exit_zones:
        try:
            paths[exit_zone] = nx.shortest_path(G, source, exit_zone, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    return paths


def compute_graph_centrality() -> dict[str, float]:
    """Compute betweenness centrality for all zones.

    Higher centrality = zone is a critical bottleneck/corridor.

    Returns:
        Dict mapping zone_id → centrality score (0-1).
    """
    G = build_spatial_graph()
    return nx.betweenness_centrality(G, weight="weight")


def recommend_optimal_room(
    people: int,
    exclude_zones: list[str] | None = None,
) -> str | None:
    """Recommend the optimal room for a booking based on capacity and freedom.

    Selects the room with lowest distortion that fits the people count,
    preferring rooms that are not corridors/WCs.

    Args:
        people: Number of expected occupants.
        exclude_zones: Zone IDs to exclude from consideration.

    Returns:
        Zone ID of the recommended room, or None if none fit.
    """
    exclude = set(exclude_zones or [])
    # Exclude non-bookable zones
    exclude.update(["p0_circulacao", "p1_circulacao", "p0_wc", "p0_hall"])

    best_zone = None
    best_score = float("inf")

    for zone_id in _ZONE_ADJACENCY:
        if zone_id in exclude:
            continue
        zone = get_zone_by_id(zone_id)
        if not zone or zone.capacity < people:
            continue
        # Score: lower distortion + less wasted capacity = better
        try:
            d_result = compute_distortion(zone_id)
            wasted = zone.capacity - people
            score = d_result.D + wasted * 0.01
            if score < best_score:
                best_score = score
                best_zone = zone_id
        except Exception:
            continue

    return best_zone


# ═══════════════════════════════════════════════
# Core AFI Computations
# ═══════════════════════════════════════════════


def compute_perception(
    zone_id: str,
    sensor_type: str = "cheap_iot",
    config: AFIConfig | None = None,
) -> PerceptionResult:
    """Compute Perception (P) for a zone.

    P = log2(N) * T
    where N = number of distinguishable paths (exits), T = predictive depth.

    Args:
        zone_id: Zone identifier.
        sensor_type: Sensor quality ('cheap_iot', 'matter', 'ai_vision').
        config: AFI configuration. Defaults to global config.

    Returns:
        PerceptionResult with P score.
    """
    cfg = config or DEFAULT_AFI_CONFIG

    # N = number of adjacent zones (exits/paths)
    neighbors = _ZONE_ADJACENCY.get(zone_id, [])
    N = max(1, len(neighbors))

    # T = predictive depth based on sensor quality
    sensor_depths = {
        "cheap_iot": cfg.sensor_depth_cheap_iot,
        "matter": cfg.sensor_depth_matter,
        "ai_vision": cfg.sensor_depth_ai_vision,
    }
    T = sensor_depths.get(sensor_type, cfg.sensor_depth_cheap_iot)

    # P = log2(N) * T
    P = math.log2(N) * T if N > 1 else 0.1 * T  # Minimum perception for dead-ends

    return PerceptionResult(zone_id=zone_id, N=N, T=T, P=round(P, 4))


def compute_distortion(
    zone_id: str,
    config: AFIConfig | None = None,
    overrides: dict[str, float] | None = None,
) -> DistortionResult:
    """Compute Geometric Distortion (D) for a zone.

    D = exp(Σ w_k · ln(d_k) + Σ γ_jk · ln(d_j) · ln(d_k))
    Rejects additive models: uses log-linear interaction model to capture
    synergistic barriers (e.g., fire + blocked exit).

    Args:
        zone_id: Zone identifier.
        config: AFI configuration.
        overrides: Optional dict of barrier overrides (e.g., {"fire": 100.0}).

    Returns:
        DistortionResult with D score.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    overrides = overrides or {}

    # Compute barrier values from sensor data
    d_temp = _compute_temperature_barrier(zone_id, cfg)
    d_co2 = _compute_co2_barrier(zone_id, cfg)
    d_crowd = _compute_crowding_barrier(zone_id)
    d_exit = overrides.get("blocked_exit", 1.0)
    d_fire = overrides.get("fire", 1.0)

    barriers = {
        "temperature": d_temp,
        "co2": d_co2,
        "crowding": d_crowd,
        "blocked_exit": d_exit,
    }

    weights = {
        "temperature": cfg.w_temperature,
        "co2": cfg.w_co2,
        "crowding": cfg.w_crowding,
        "blocked_exit": cfg.w_blocked_exit,
    }

    # Clamp barriers to minimum 1.0 (no barrier = 1.0, D converges to 1.0)
    for k in barriers:
        barriers[k] = max(1.0, barriers[k])

    # Main distortion: Σ w_k · ln(d_k)
    main_term = sum(weights[k] * math.log(barriers[k]) for k in barriers)

    # Interaction terms: γ_jk · ln(d_j) · ln(d_k)
    interactions: dict[str, float] = {}
    interaction_term = 0.0

    # Fire + blocked exit synergy
    if d_fire > 1.0 and d_exit > 1.0:
        gamma = cfg.gamma_fire_exit
        interaction = gamma * math.log(d_fire) * math.log(d_exit)
        interaction_term += interaction
        interactions["fire_x_exit"] = round(interaction, 4)

    # CO2 + crowding synergy
    if d_co2 > 1.5 and d_crowd > 1.5:
        gamma = cfg.gamma_co2_crowd
        interaction = gamma * math.log(d_co2) * math.log(d_crowd)
        interaction_term += interaction
        interactions["co2_x_crowd"] = round(interaction, 4)

    # D = exp(main + interactions)
    D = math.exp(main_term + interaction_term)

    # Clamp to reasonable range (1.0 = no distortion, 1000.0 = extreme)
    D = max(1.0, min(1000.0, D))

    return DistortionResult(
        zone_id=zone_id,
        barriers={k: round(v, 4) for k, v in barriers.items()},
        weights={k: round(v, 4) for k, v in weights.items()},
        interactions=interactions,
        D=round(D, 4),
    )


def compute_freedom(
    zone_id: str,
    sensor_type: str = "cheap_iot",
    config: AFIConfig | None = None,
    distortion_overrides: dict[str, float] | None = None,
) -> FreedomResult:
    """Compute Freedom (F = P / D) for a zone.

    The ultimate index of spatial health. Higher = better.

    Args:
        zone_id: Zone identifier.
        sensor_type: Sensor quality level.
        config: AFI configuration.
        distortion_overrides: Optional barrier overrides.

    Returns:
        FreedomResult with F score.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    perception = compute_perception(zone_id, sensor_type, cfg)
    distortion = compute_distortion(zone_id, cfg, distortion_overrides)

    F = perception.P / distortion.D if distortion.D > 0 else 0.0

    return FreedomResult(
        zone_id=zone_id,
        P=perception.P,
        D=distortion.D,
        F=round(F, 4),
    )


def compute_financial_bleed(
    zone_id: str,
    config: AFIConfig | None = None,
) -> FinancialBleed:
    """Compute real-time financial cost of inefficiencies for a zone.

    Combines:
    1. Energy cost = total_kwh * cost_per_kwh (hourly)
    2. Open window penalty = ΔT · Volume · ρ · c_p · HVAC_eff⁻¹ · cost_per_kwh
    3. Human capital loss = Σ (1 - ComfortIndex/100) · Occupants · Wage · Impact

    Args:
        zone_id: Zone identifier.
        config: AFI configuration.

    Returns:
        FinancialBleed with per-component and total costs.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    zone = get_zone_by_id(zone_id)
    if zone is None:
        return FinancialBleed(zone_id=zone_id)

    # ── 1. Energy Cost (€/hr) ──────────────────────
    energy_cost = _compute_energy_cost(zone_id, cfg)

    # ── 2. Open Window Penalty (€/hr) ─────────────
    window_penalty = _compute_open_window_penalty(zone_id, zone.area_m2, cfg)

    # ── 3. Human Capital Loss (€/hr) ──────────────
    human_loss = _compute_human_capital_loss(zone_id, cfg)

    total = min(energy_cost + window_penalty + human_loss, MAX_ZONE_BLEED_EUR_HR)

    return FinancialBleed(
        zone_id=zone_id,
        energy_cost_eur_hr=round(energy_cost, 4),
        open_window_penalty_eur_hr=round(window_penalty, 4),
        human_capital_loss_eur_hr=round(human_loss, 4),
        total_bleed_eur_hr=round(total, 4),
    )


def compute_risk_cost(
    zone_id: str,
    hazard_type: str = "fire",
    config: AFIConfig | None = None,
) -> RiskAssessment:
    """Compute catastrophic risk cost for a zone.

    Risk_Cost = P(Hazard) × (Asset_Value + N_people × Human_Life_Value_Proxy)

    Args:
        zone_id: Zone identifier.
        hazard_type: Type of hazard ('fire', 'flood', 'structural').
        config: AFI configuration.

    Returns:
        RiskAssessment with probability and expected cost.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    zone = get_zone_by_id(zone_id)

    # Get current occupancy
    n_people = 0
    occ_df = store.get_zone_data("occupancy", zone_id)
    if not occ_df.empty:
        n_people = int(
            occ_df.sort_values("timestamp").iloc[-1].get("occupant_count", 0)
        )

    # Base probability scaled by zone conditions
    prob = cfg.base_fire_probability
    if hazard_type == "fire":
        # Higher probability if temperature anomalies detected
        comfort_df = store.get_zone_data("comfort", zone_id)
        if not comfort_df.empty:
            latest = comfort_df.sort_values("timestamp").iloc[-1]
            temp = latest.get("temperature_c", 22)
            if temp and temp > 28:
                prob *= 2.0  # Elevated risk

    # Asset value proportional to zone area
    area = zone.area_m2 if zone else 30.0
    zone_asset = cfg.asset_value_eur * (area / 800.0)  # ~800m² total building

    # Risk = P(hazard) × (zone_asset + N × life_value)
    risk_cost = prob * (zone_asset + n_people * cfg.human_life_value_proxy)

    return RiskAssessment(
        zone_id=zone_id,
        hazard_probability=round(prob, 8),
        risk_cost_eur=round(risk_cost, 2),
    )


def update_stigmergy(
    current: StigmergyState | None = None,
    freedom_scores: dict[str, float] | None = None,
    config: AFIConfig | None = None,
) -> StigmergyState:
    """Update swarm stigmergy pheromone trails.

    φ_e(t+1) = (1 - ρ) · φ_e(t) + η · F_e(t)
    where ρ = evaporation rate, η = deposit rate, F_e = avg freedom of edge endpoints.

    Args:
        current: Current stigmergy state. Defaults to uniform pheromones.
        freedom_scores: Dict zone_id → freedom score. Defaults to computed values.
        config: AFI configuration.

    Returns:
        Updated StigmergyState.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    rho = cfg.evaporation_rate
    eta = cfg.deposit_rate

    # Initialize if needed
    if current is None:
        current = StigmergyState(
            edges={f"{a}->{b}": 1.0 for a, b in _ZONE_EDGES},
        )

    # Compute freedom scores if not provided
    if freedom_scores is None:
        freedom_scores = {}
        for zone in get_monitored_zones():
            try:
                result = compute_freedom(zone.id, config=cfg)
                freedom_scores[zone.id] = result.F
            except Exception:
                freedom_scores[zone.id] = 0.5

    # Update each edge
    new_edges: dict[str, float] = {}
    for a, b in _ZONE_EDGES:
        edge_id = f"{a}->{b}"
        phi_old = current.edges.get(edge_id, 1.0)

        # F_e = average freedom of edge endpoints
        f_a = freedom_scores.get(a, 0.5)
        f_b = freedom_scores.get(b, 0.5)
        F_e = (f_a + f_b) / 2.0

        # φ_e(t+1) = (1 - ρ) · φ_e(t) + η · F_e(t)
        phi_new = (1 - rho) * phi_old + eta * F_e
        new_edges[edge_id] = round(max(0.01, phi_new), 4)

    return StigmergyState(edges=new_edges, timestamp=datetime.now())


def compute_building_afi(
    config: AFIConfig | None = None,
    sensor_deployment: dict[str, str] | None = None,
) -> BuildingAFI:
    """Compute complete AFI assessment for the entire building.

    Args:
        config: AFI configuration. Defaults to global config.
        sensor_deployment: Dict zone_id → sensor_type. Defaults to cheap_iot.

    Returns:
        BuildingAFI with per-zone and aggregate results.
    """
    cfg = config or DEFAULT_AFI_CONFIG
    sensor_deployment = sensor_deployment or {}

    zones_afi: dict[str, ZoneAFI] = {}
    freedom_scores: dict[str, float] = {}
    total_bleed = 0.0
    total_risk = 0.0
    freedom_values: list[float] = []

    for zone in get_monitored_zones():
        try:
            sensor_type = sensor_deployment.get(zone.id, "cheap_iot")
            perception = compute_perception(zone.id, sensor_type, cfg)
            distortion = compute_distortion(zone.id, cfg)
            raw_f = round(perception.P / distortion.D, 4) if distortion.D > 0 else 0.0
            smoothed_f = _ema_smooth(zone.id, "freedom", raw_f)
            freedom = FreedomResult(
                zone_id=zone.id,
                P=perception.P,
                D=distortion.D,
                F=round(smoothed_f, 4),
            )
            financial = compute_financial_bleed(zone.id, cfg)
            smoothed_bleed = _ema_smooth(zone.id, "bleed", financial.total_bleed_eur_hr)
            financial.total_bleed_eur_hr = round(smoothed_bleed, 4)
            risk = compute_risk_cost(zone.id, config=cfg)

            zones_afi[zone.id] = ZoneAFI(
                zone_id=zone.id,
                perception=perception,
                distortion=distortion,
                freedom=freedom,
                financial=financial,
                risk=risk,
            )

            freedom_scores[zone.id] = freedom.F
            freedom_values.append(freedom.F)
            total_bleed += financial.total_bleed_eur_hr
            total_risk += risk.risk_cost_eur

        except Exception as e:
            logger.warning(f"AFI computation failed for {zone.id}: {e}")

    # Compute stigmergy
    stigmergy = update_stigmergy(freedom_scores=freedom_scores, config=cfg)

    avg_freedom = float(np.mean(freedom_values)) if freedom_values else 0.0

    logger.info(
        f"Building AFI: avg_freedom={avg_freedom:.2f}, "
        f"total_bleed=€{total_bleed:.2f}/hr, "
        f"total_risk=€{total_risk:.2f}"
    )

    return BuildingAFI(
        zones=zones_afi,
        stigmergy=stigmergy,
        total_financial_bleed_eur_hr=round(
            min(total_bleed, MAX_BUILDING_BLEED_EUR_HR), 4
        ),
        avg_freedom=round(avg_freedom, 4),
        total_risk_eur=round(total_risk, 2),
    )


# ═══════════════════════════════════════════════
# Private Barrier Computations
# ═══════════════════════════════════════════════


def _compute_temperature_barrier(zone_id: str, cfg: AFIConfig) -> float:
    """Compute temperature deviation barrier (d_temp >= 1.0).

    d_temp = 1 + |T_actual - T_optimal| / T_optimal_range

    Args:
        zone_id: Zone identifier.
        cfg: AFI configuration.

    Returns:
        Barrier value (1.0 = no barrier, higher = worse).
    """
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df.empty:
        return 1.0

    latest = comfort_df.sort_values("timestamp").iloc[-1]
    temp = latest.get("temperature_c")
    if temp is None or np.isnan(temp):
        return 1.0

    deviation = abs(float(temp) - cfg.optimal_temperature_c)
    band = COMFORT_BANDS.get("temperature")
    optimal_range = (band.max_optimal - band.min_optimal) if band else 4.0

    return 1.0 + deviation / optimal_range


def _compute_co2_barrier(zone_id: str, cfg: AFIConfig) -> float:
    """Compute CO2 excess barrier (d_co2 >= 1.0).

    d_co2 = 1 + max(0, CO2_actual - CO2_optimal) / CO2_optimal

    Args:
        zone_id: Zone identifier.
        cfg: AFI configuration.

    Returns:
        Barrier value.
    """
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df.empty:
        return 1.0

    latest = comfort_df.sort_values("timestamp").iloc[-1]
    co2 = latest.get("co2_ppm")
    if co2 is None or np.isnan(co2):
        return 1.0

    excess = max(0.0, float(co2) - cfg.optimal_co2_ppm)
    return 1.0 + excess / cfg.optimal_co2_ppm


def _compute_crowding_barrier(zone_id: str) -> float:
    """Compute overcrowding barrier (d_crowd >= 1.0).

    d_crowd = 1 + max(0, occupancy_ratio - 0.8) * 5

    Args:
        zone_id: Zone identifier.

    Returns:
        Barrier value.
    """
    zone = get_zone_by_id(zone_id)
    if zone is None or zone.capacity == 0:
        return 1.0

    occ_df = store.get_zone_data("occupancy", zone_id)
    if occ_df.empty:
        return 1.0

    latest = occ_df.sort_values("timestamp").iloc[-1]
    ratio = latest.get("occupancy_ratio", 0)
    if ratio is None or np.isnan(ratio):
        return 1.0

    excess = max(0.0, float(ratio) - 0.8)
    return 1.0 + excess * 5.0


def _compute_energy_cost(zone_id: str, cfg: AFIConfig) -> float:
    """Compute hourly energy cost for a zone.

    Cost = total_kwh_latest * cost_per_kwh (annualized to hourly)

    Args:
        zone_id: Zone identifier.
        cfg: AFI configuration.

    Returns:
        Energy cost in €/hr.
    """
    energy_df = store.get_zone_data("energy", zone_id)
    if energy_df.empty:
        return 0.0

    latest = energy_df.sort_values("timestamp").iloc[-1]
    total_kwh = float(latest.get("total_kwh", 0))

    # Data is at 15-min intervals, so multiply by 4 for hourly rate
    return total_kwh * 4.0 * cfg.cost_per_kwh


def _compute_open_window_penalty(zone_id: str, area_m2: float, cfg: AFIConfig) -> float:
    """Compute HVAC penalty when indoor/outdoor temperature differs.

    Cost = ΔT · Volume · ρ · c_p · HVAC_eff⁻¹ · cost_per_kwh / 3600

    Args:
        zone_id: Zone identifier.
        area_m2: Zone area.
        cfg: AFI configuration.

    Returns:
        Open window penalty in €/hr.
    """
    comfort_df = store.get_zone_data("comfort", zone_id)
    weather_df = store.get("weather")

    if comfort_df.empty:
        return 0.0
    if weather_df.empty:
        return 0.0

    indoor_temp = comfort_df.sort_values("timestamp").iloc[-1].get("temperature_c")
    outdoor_temp = weather_df.sort_values("timestamp").iloc[-1].get("outdoor_temp_c")

    if indoor_temp is None or outdoor_temp is None:
        return 0.0
    if np.isnan(indoor_temp) or np.isnan(outdoor_temp):
        return 0.0

    delta_t = abs(float(indoor_temp) - float(outdoor_temp))

    # Only penalize if significant drift (> 3°C indicates possible open window)
    if delta_t < 3.0:
        return 0.0

    volume = area_m2 * cfg.ceiling_height_m  # m³
    # Energy to heat/cool: Q = ρ · V · c_p · ΔT (kJ) → kWh / 3600
    q_kwh = (cfg.air_density * volume * cfg.air_specific_heat * delta_t) / 3600.0
    cost = q_kwh * (1.0 / cfg.hvac_efficiency) * cfg.cost_per_kwh

    return max(0.0, cost)


def _compute_human_capital_loss(zone_id: str, cfg: AFIConfig) -> float:
    """Compute productivity loss from poor comfort conditions.

    Loss = (1 - ComfortIndex/100) × Occupants × Wage × ImpactFactor

    Args:
        zone_id: Zone identifier.
        cfg: AFI configuration.

    Returns:
        Human capital loss in €/hr.
    """
    # Get current occupancy
    occ_df = store.get_zone_data("occupancy", zone_id)
    if occ_df.empty:
        return 0.0

    latest_occ = occ_df.sort_values("timestamp").iloc[-1]
    n_people = int(latest_occ.get("occupant_count", 0))
    if n_people == 0:
        return 0.0

    # Compute comfort index (0-100) from comfort data
    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df.empty:
        return 0.0

    latest = comfort_df.sort_values("timestamp").iloc[-1]
    comfort_score = _compute_comfort_index(latest)

    # Loss = (1 - comfort/100) * occupants * wage * impact
    loss = (
        (1.0 - comfort_score / 100.0)
        * n_people
        * cfg.avg_hourly_wage
        * cfg.impact_factor
    )

    return max(0.0, loss)


def _compute_comfort_index(latest_reading: Any) -> float:
    """Compute a 0-100 comfort index from latest sensor reading.

    Args:
        latest_reading: Latest comfort DataFrame row.

    Returns:
        Comfort index (100 = perfect, 0 = terrible).
    """
    scores: list[float] = []

    temp = latest_reading.get("temperature_c")
    if temp is not None and not np.isnan(temp):
        band = COMFORT_BANDS.get("temperature")
        if band:
            if band.min_optimal <= temp <= band.max_optimal:
                scores.append(100.0)
            elif band.min_acceptable <= temp <= band.max_acceptable:
                scores.append(70.0)
            else:
                scores.append(30.0)

    co2 = latest_reading.get("co2_ppm")
    if co2 is not None and not np.isnan(co2):
        band = COMFORT_BANDS.get("co2")
        if band:
            if band.min_optimal <= co2 <= band.max_optimal:
                scores.append(100.0)
            elif band.min_acceptable <= co2 <= band.max_acceptable:
                scores.append(70.0)
            else:
                scores.append(30.0)

    humidity = latest_reading.get("humidity_pct")
    if humidity is not None and not np.isnan(humidity):
        band = COMFORT_BANDS.get("humidity")
        if band:
            if band.min_optimal <= humidity <= band.max_optimal:
                scores.append(100.0)
            elif band.min_acceptable <= humidity <= band.max_acceptable:
                scores.append(70.0)
            else:
                scores.append(30.0)

    return float(np.mean(scores)) if scores else 50.0
