"""Emergency Mode page callbacks.

Registers callbacks for rendering the emergency floorplan with danger zones,
exit markers, evacuation paths, status KPIs, and scenario recommendations.
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from loguru import logger

from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
)
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback

# ── Exit positions per floor (meters) ─────────
_FLOOR_EXITS: dict[int, list[dict[str, object]]] = {
    0: [
        {"x": 0, "y": 9.25, "label": "Main Entrance"},
        {"x": 15, "y": 18.3, "label": "North Exit"},
        {"x": 30.3, "y": 9.25, "label": "East Exit"},
    ],
    1: [
        {"x": 0, "y": 9.25, "label": "Stairwell A"},
        {"x": 30.3, "y": 9.25, "label": "Stairwell B"},
    ],
}

# ── Scenario recommendations ─────────────────
_SCENARIO_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "fire": {
        "title": "Fire Response Protocol",
        "icon": "mdi:fire",
        "color": STATUS_CRITICAL,
        "text": (
            "1. Activate fire alarm and call 112 immediately.\n"
            "2. Evacuate all occupants via marked emergency exits "
            "(shown in green on the floorplan).\n"
            "3. Do NOT use elevators. Close doors behind you to "
            "contain the fire.\n"
            "4. Assemble at the designated meeting point in the "
            "parking area (east side).\n"
            "5. Facility manager must verify all zones are clear "
            "before allowing re-entry."
        ),
    },
    "smoke": {
        "title": "Smoke Detection Protocol",
        "icon": "mdi:smoke-detector-variant",
        "color": STATUS_WARNING,
        "text": (
            "1. Identify the source of smoke and assess severity.\n"
            "2. If smoke is heavy or source is unclear, treat as fire "
            "and evacuate immediately.\n"
            "3. Close HVAC systems to prevent smoke spread.\n"
            "4. Notify building management and emergency services.\n"
            "5. Keep low to the ground if smoke is present in "
            "evacuation routes."
        ),
    },
    "evacuation": {
        "title": "General Evacuation Procedure",
        "icon": "mdi:exit-run",
        "color": ACCENT_BLUE,
        "text": (
            "1. Follow the illuminated evacuation routes to the "
            "nearest emergency exit.\n"
            "2. Assist persons with reduced mobility.\n"
            "3. Do NOT return to collect personal belongings.\n"
            "4. Floor wardens must sweep their assigned zones.\n"
            "5. Report to the assembly point and confirm headcount "
            "with the safety coordinator."
        ),
    },
    "lockdown": {
        "title": "Lockdown Protocol",
        "icon": "mdi:lock-alert",
        "color": STATUS_CRITICAL,
        "text": (
            "1. Secure all external doors and windows immediately.\n"
            "2. Move to the nearest interior room away from windows.\n"
            "3. Lock or barricade the door. Turn off lights.\n"
            "4. Silence all mobile devices.\n"
            "5. Wait for the all-clear signal from security or "
            "emergency services before moving."
        ),
    },
}


def register_emergency_callbacks(app: object) -> None:
    """Register all Emergency Mode page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_main_callback(app)


def _register_main_callback(app: object) -> None:
    """Register the main callback that updates floorplan, KPIs, and recommendations.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("emergency-floorplan", "figure"),
        Output("emergency-status-panel", "children"),
        Output("emergency-recommendation", "children"),
        Input("emergency-scenario", "value"),
        Input("emergency-zone-origin", "value"),
        Input("emergency-floor-selector", "value"),
        State("building-state-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_emergency_view(
        scenario: str | None,
        zone_origin: str | None,
        floor_str: str | None,
        building_state: dict | None,
        pathname: str | None,
    ) -> tuple:
        """Update the emergency floorplan, status KPIs, and recommendation card.

        Args:
            scenario: Selected emergency scenario (fire/smoke/evacuation/lockdown).
            zone_origin: Zone ID where the incident originates.
            floor_str: Selected floor as string ("0" or "1").
            building_state: Current building state data from the store.
            pathname: Current page URL path.

        Returns:
            Tuple of (floorplan figure, status panel children,
            recommendation card children).
        """
        if pathname != "/view_emergency":
            return no_update, no_update, no_update

        from core.afi_engine import get_shortest_path
        from views.floorplan.renderer_2d import render_floorplan_2d
        from views.floorplan.zones_geometry import (
            get_zone_center,
            get_zones_for_floor,
        )

        floor = int(floor_str) if floor_str else 0
        scenario = scenario or "evacuation"

        # ── 1. Render base floorplan ───────────
        fig = render_floorplan_2d(floor=floor, zone_data=None)

        # ── 2. Color danger zone red ───────────
        floor_zones = get_zones_for_floor(floor)
        floor_zone_ids = {z.id for z in floor_zones}

        if zone_origin and zone_origin in floor_zone_ids:
            origin_center = get_zone_center(zone_origin)

            # Add a prominent red marker at the incident zone
            fig.add_trace(
                go.Scatter(
                    x=[origin_center[0]],
                    y=[origin_center[1]],
                    mode="markers+text",
                    marker=dict(
                        size=20,
                        color=STATUS_CRITICAL,
                        opacity=0.8,
                        symbol="x",
                        line=dict(width=2, color="#FFFFFF"),
                    ),
                    text=["INCIDENT"],
                    textposition="top center",
                    textfont=dict(size=10, color=STATUS_CRITICAL),
                    hovertext=[f"Incident Zone: {zone_origin}"],
                    hoverinfo="text",
                    showlegend=False,
                )
            )

            # Overlay a red semi-transparent shape on the danger zone
            for shape in fig.layout.shapes:
                if hasattr(shape, "name") and shape.name == zone_origin:
                    shape.fillcolor = "rgba(255, 59, 48, 0.45)"
                    shape.line.color = STATUS_CRITICAL
                    shape.line.width = 3

        # ── 3. Add exit markers (green triangles) ──
        exits = _FLOOR_EXITS.get(floor, [])
        exit_x = [e["x"] for e in exits]
        exit_y = [e["y"] for e in exits]
        exit_labels = [e["label"] for e in exits]

        fig.add_trace(
            go.Scatter(
                x=exit_x,
                y=exit_y,
                mode="markers+text",
                marker=dict(
                    size=16,
                    color=STATUS_HEALTHY,
                    symbol="triangle-up",
                    line=dict(width=1.5, color="#FFFFFF"),
                ),
                text=exit_labels,
                textposition="bottom center",
                textfont=dict(size=9, color=STATUS_HEALTHY),
                hovertext=[f"Emergency Exit: {lbl}" for lbl in exit_labels],
                hoverinfo="text",
                showlegend=False,
            )
        )

        # ── 4. Draw evacuation paths ──────────
        if zone_origin and zone_origin in floor_zone_ids:
            if scenario in ("evacuation", "fire"):
                # Find corridor zone for the current floor
                corridor_id = f"p{floor}_circulacao"

                for exit_info in exits:
                    try:
                        path_zone_ids = get_shortest_path(zone_origin, corridor_id)
                    except Exception:
                        # Fallback: direct line from origin to exit
                        path_zone_ids = [zone_origin]

                    # Build waypoints from zone centroids
                    path_x = []
                    path_y = []
                    for zid in path_zone_ids:
                        cx, cy = get_zone_center(zid)
                        path_x.append(cx)
                        path_y.append(cy)

                    # Extend path to the exit position
                    path_x.append(exit_info["x"])
                    path_y.append(exit_info["y"])

                    fig.add_trace(
                        go.Scatter(
                            x=path_x,
                            y=path_y,
                            mode="lines",
                            line=dict(
                                color=STATUS_HEALTHY,
                                width=3,
                                dash="dot",
                            ),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )

        # ── 5. Build KPI cards ─────────────────
        zones_affected = _count_affected_zones(scenario, zone_origin, floor_zones)
        people_at_risk = _estimate_people_at_risk(
            zone_origin, floor_zones, building_state
        )
        evac_time = _estimate_evacuation_time(scenario, floor)
        exit_count = len(exits)

        status_children = html.Div(
            [
                create_kpi_card(
                    title="Zones Affected",
                    value=str(zones_affected),
                    icon="mdi:map-marker-alert-outline",
                ),
                create_kpi_card(
                    title="Estimated Evacuation Time",
                    value=f"{evac_time}",
                    unit="min",
                    icon="mdi:timer-alert-outline",
                ),
                create_kpi_card(
                    title="People at Risk",
                    value=str(people_at_risk),
                    icon="mdi:account-alert-outline",
                ),
                create_kpi_card(
                    title="Exit Routes Available",
                    value=str(exit_count),
                    icon="mdi:door-open",
                ),
            ],
            className="grid-4",
        )

        # ── 6. Build recommendation card ───────
        rec_data = _SCENARIO_RECOMMENDATIONS.get(scenario, {})
        rec_title = rec_data.get("title", "Emergency Protocol")
        rec_icon = rec_data.get("icon", "mdi:shield-alert-outline")
        rec_color = rec_data.get("color", ACCENT_BLUE)
        rec_text = rec_data.get("text", "Select a scenario to view recommendations.")

        # Format the recommendation text with line breaks
        rec_lines = rec_text.split("\n")
        rec_elements = []
        for line in rec_lines:
            rec_elements.append(
                html.P(
                    line,
                    style={
                        "margin": "4px 0",
                        "fontSize": "13px",
                        "color": TEXT_PRIMARY,
                        "lineHeight": "1.5",
                    },
                )
            )

        recommendation_children = html.Div(
            [
                html.Div(
                    [
                        DashIconify(
                            icon=rec_icon,
                            width=22,
                            color=rec_color,
                        ),
                        html.Span(
                            rec_title,
                            style={
                                "fontWeight": 600,
                                "fontSize": "15px",
                                "color": TEXT_PRIMARY,
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "12px",
                    },
                ),
                html.Div(rec_elements),
            ],
            style={"padding": "16px 20px"},
        )

        logger.info(
            f"Emergency view updated: scenario={scenario}, "
            f"zone_origin={zone_origin}, floor={floor}"
        )

        return fig, status_children, recommendation_children


# ═══════════════════════════════════════════════
# Private Helpers
# ═══════════════════════════════════════════════


def _count_affected_zones(
    scenario: str,
    zone_origin: str | None,
    floor_zones: list,
) -> int:
    """Estimate the number of affected zones based on scenario.

    Args:
        scenario: Emergency scenario type.
        zone_origin: Zone ID of the incident origin.
        floor_zones: List of ZoneGeometry on the current floor.

    Returns:
        Estimated number of affected zones.
    """
    if not zone_origin:
        return 0

    total = len(floor_zones)
    if scenario in ("fire", "smoke"):
        # Fire/smoke affects adjacent zones progressively
        return min(total, max(3, total // 2))
    if scenario == "evacuation":
        # Full floor evacuation
        return total
    if scenario == "lockdown":
        # Lockdown affects all zones
        return total
    return 1


def _estimate_people_at_risk(
    zone_origin: str | None,
    floor_zones: list,
    building_state: dict | None,
) -> int:
    """Estimate the number of people at risk.

    Args:
        zone_origin: Zone ID of the incident origin.
        floor_zones: List of ZoneGeometry on the current floor.
        building_state: Current building state data.

    Returns:
        Estimated number of people at risk.
    """
    if not zone_origin:
        return 0

    # Try to get real occupancy from building state
    if building_state and isinstance(building_state, dict):
        zones_data = building_state.get("zones", {})
        total_occ = 0
        for z in floor_zones:
            zd = zones_data.get(z.id, {})
            if isinstance(zd, dict):
                total_occ += zd.get("occupant_count", 0)
        if total_occ > 0:
            return total_occ

    # Fallback: estimate from zone capacities
    return sum(z.capacity for z in floor_zones if z.capacity > 0)


def _estimate_evacuation_time(scenario: str, floor: int) -> int:
    """Estimate evacuation time in minutes.

    Args:
        scenario: Emergency scenario type.
        floor: Floor number (0 or 1).

    Returns:
        Estimated evacuation time in minutes.
    """
    base_time = 3 if floor == 0 else 5  # Upper floor takes longer
    scenario_multiplier = {
        "fire": 1.5,
        "smoke": 1.3,
        "evacuation": 1.0,
        "lockdown": 0.0,  # No evacuation in lockdown
    }
    multiplier = scenario_multiplier.get(scenario, 1.0)
    if multiplier == 0.0:
        return 0
    return int(base_time * multiplier)
