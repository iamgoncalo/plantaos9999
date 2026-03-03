"""Simulation page callbacks.

Registers callbacks for triggering simulations, rendering timeline charts,
damage summaries, and affected zone lists.
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from dash_iconify import DashIconify
from loguru import logger

from config.building import get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from core.afi.pso import PSOConfig, optimize_hvac_setpoints
from core.simulation import SimulationResult, simulate_scope
from utils.simulation_helpers import (
    SCENARIO_ROI,
    empty_affected_zones,
    empty_damage_summary,
)
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback

# HVAC event types that benefit from PSO setpoint optimization
_HVAC_SCENARIOS: set[str] = {
    "hvac_failure",
    "hvac_night_off",
    "setpoint_adjust",
    "open_window",
}


def register_simulation_callbacks(app: object) -> None:
    """Register all simulation page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_scope_toggle(app)
    _register_trigger(app)
    _register_timeline(app)
    _register_damage_summary(app)
    _register_affected_zones(app)


# ═══════════════════════════════════════════════
# Callback 0: Scope Toggle (show/hide zone dropdown)
# ═══════════════════════════════════════════════


def _register_scope_toggle(app: object) -> None:
    """Toggle zone selector visibility based on scope selection.

    Args:
        app: The Dash application instance.
    """
    app.clientside_callback(
        """
        function(scope) {
            if (scope === 'zone') {
                return {'marginBottom': '20px', 'display': 'block'};
            }
            return {'marginBottom': '20px', 'display': 'none'};
        }
        """,
        Output("sim-zone-selector-wrapper", "style"),
        Input("sim-scope-selector", "value"),
    )


# ═══════════════════════════════════════════════
# Callback 1: Trigger Simulation
# ═══════════════════════════════════════════════


def _register_trigger(app: object) -> None:
    """Register the confirm dialog + simulation trigger callbacks.

    Button click opens a confirm dialog. On confirmation, creates a
    SimulationEvent from the form state, runs simulate_event(),
    and stores the serialized result in sim-result-store.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("sim-confirm-dialog", "displayed"),
        Input("sim-trigger-btn", "n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_sim_confirm(n_clicks: int | None, pathname: str | None) -> bool:
        """Open confirmation dialog before running simulation."""
        if pathname != "/simulation" or not n_clicks:
            return False
        return True

    @app.callback(
        Output("sim-result-store", "data"),
        Output("sim-trigger-btn", "children"),
        Input("sim-confirm-dialog", "submit_n_clicks"),
        State("sim-event-type", "value"),
        State("sim-scope-selector", "value"),
        State("sim-zone-selector", "value"),
        State("sim-intensity-slider", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_simulation(
        n_clicks: int | None,
        event_type: str | None,
        scope: str | None,
        zone_id: str | None,
        intensity: float | None,
        pathname: str | None,
    ) -> tuple[dict | object, str | object]:
        """Run the simulation engine and store the result.

        Args:
            n_clicks: Button click count.
            event_type: Selected event type string.
            scope: Scope selector value (building/floor_0/floor_1/zone).
            zone_id: Selected zone identifier (used when scope='zone').
            intensity: Intensity slider value (0.1-1.0).
            pathname: Current page URL path.

        Returns:
            Tuple of (serialized SimulationResult dict, button text).
        """
        if pathname != "/simulation":
            return (no_update, no_update)

        if not n_clicks or not event_type:
            return (no_update, no_update)

        scope = scope or "zone"
        effective_scope = zone_id if scope == "zone" else scope

        if scope == "zone" and not zone_id:
            return (no_update, no_update)

        try:
            result: SimulationResult = simulate_scope(
                event_type=event_type,
                scope=effective_scope,
                intensity=intensity or 0.8,
                duration_hours=24,
                step_minutes=15,
            )
            logger.info(
                f"Simulation complete: {event_type} scope={effective_scope}, "
                f"damage=€{result.total_financial_damage_eur:.2f}"
            )

            data = result.model_dump(mode="json")

            # For HVAC scenarios, run PSO to find optimal setpoints
            if event_type in _HVAC_SCENARIOS and result.timeline:
                try:
                    last_step = result.timeline[-1]
                    zone_states = {
                        z: {
                            "temperature_c": last_step.temperature_c,
                            "co2_ppm": last_step.co2_ppm,
                            "humidity_pct": 55.0,
                            "occupant_count": last_step.occupant_count,
                        }
                        for z in result.zones_affected[:3]
                    }
                    if zone_states:
                        pso_recs = optimize_hvac_setpoints(
                            zone_states,
                            config=PSOConfig(n_particles=20, max_iter=30, seed=42),
                        )
                        data["pso_recommendations"] = pso_recs
                        logger.info(f"PSO recommendations: {len(pso_recs)} zones")
                except Exception as pso_err:
                    logger.warning(f"PSO optimization skipped: {pso_err}")

            return (data, "Results Ready")
        except Exception as exc:
            logger.error(f"Simulation trigger error: {exc}")
            return (no_update, no_update)


# ═══════════════════════════════════════════════
# Callback 2: Timeline Chart
# ═══════════════════════════════════════════════


def _register_timeline(app: object) -> None:
    """Register the callback that renders the simulation timeline chart.

    Plots three traces on a dual y-axis layout:
      - Temperature (°C) on left y-axis
      - CO2 (ppm) on left y-axis
      - Cumulative Cost (€) on right y-axis (area fill)

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("sim-timeline-chart", "figure"),
        Input("sim-result-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def update_timeline(
        result_data: dict | None,
        pathname: str | None,
    ) -> go.Figure:
        """Build the simulation timeline figure from stored result data.

        Args:
            result_data: Serialized SimulationResult dict from the store.
            pathname: Current page URL path.

        Returns:
            Plotly Figure with temperature, CO2, and cost traces.
        """
        if pathname != "/simulation" or not result_data:
            return empty_chart("Run a simulation to see the timeline")

        try:
            timeline = result_data.get("timeline", [])
            if not timeline:
                return empty_chart("No simulation timeline data")

            minutes = [step["minutes_elapsed"] for step in timeline]
            temperatures = [step.get("temperature_c", 22.0) for step in timeline]
            co2_values = [step.get("co2_ppm", 500.0) for step in timeline]
            cumulative_costs = [
                step.get("cumulative_cost_eur", 0.0) for step in timeline
            ]

            fig = go.Figure()

            # Temperature trace — left y-axis
            fig.add_trace(
                go.Scatter(
                    x=minutes,
                    y=temperatures,
                    mode="lines",
                    name="Temperature (°C)",
                    line=dict(color=STATUS_CRITICAL, width=2),
                    hovertemplate=("Min %{x}<br>%{y:.1f} °C<extra></extra>"),
                )
            )

            # CO2 trace — left y-axis
            fig.add_trace(
                go.Scatter(
                    x=minutes,
                    y=co2_values,
                    mode="lines",
                    name="CO₂ (ppm)",
                    line=dict(color=STATUS_WARNING, width=2),
                    hovertemplate=("Min %{x}<br>%{y:.0f} ppm<extra></extra>"),
                )
            )

            # Cumulative Cost trace — right y-axis, area fill
            fig.add_trace(
                go.Scatter(
                    x=minutes,
                    y=cumulative_costs,
                    mode="lines",
                    name="Cumulative Cost (€)",
                    line=dict(color=ACCENT_BLUE, width=2),
                    fill="tozeroy",
                    fillcolor=f"{ACCENT_BLUE}1A",
                    yaxis="y2",
                    hovertemplate=("Min %{x}<br>€%{y:.2f}<extra></extra>"),
                )
            )

            fig.update_layout(
                xaxis=dict(title="Minutes Elapsed"),
                yaxis=dict(
                    title="Temperature (°C) / CO₂ (ppm)",
                    titlefont=dict(color=TEXT_PRIMARY),
                ),
                yaxis2=dict(
                    title="Cumulative Cost (€)",
                    titlefont=dict(color=ACCENT_BLUE),
                    tickfont=dict(color=ACCENT_BLUE),
                    overlaying="y",
                    side="right",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="left",
                    x=0,
                ),
            )

            return apply_chart_theme(fig, "Simulation Timeline", height=400)
        except Exception as exc:
            logger.error(f"Timeline chart render error: {exc}")
            return empty_chart("Error rendering timeline")


# ═══════════════════════════════════════════════
# Callback 3: Damage Summary
# ═══════════════════════════════════════════════


def _register_damage_summary(app: object) -> None:
    """Register the callback that renders the savings/impact KPI cards.

    Shows four cards: Monthly Savings, Implementation, Comfort Impact,
    and Zones Affected.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("sim-damage-summary", "children"),
        Input("sim-result-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def update_damage_summary(
        result_data: dict | None,
        pathname: str | None,
    ) -> html.Div:
        """Build savings summary KPI cards from simulation result.

        Args:
            result_data: Serialized SimulationResult dict from the store.
            pathname: Current page URL path.

        Returns:
            Dash html.Div containing four KPI cards in a grid-4 layout.
        """
        if not result_data:
            return empty_damage_summary()

        try:
            total_damage = result_data.get("total_financial_damage_eur", 0.0)
            evac_time = result_data.get("evacuation_time_seconds")
            zones_affected = result_data.get("zones_affected", [])
            timeline = result_data.get("timeline", [])
            event_data = result_data.get("event", {})
            event_type = event_data.get("event_type", "")

            # Peak impact from timeline steps
            peak_impact = 1.0
            if timeline:
                peak_impact = max(
                    (step.get("distortion", 1.0) for step in timeline),
                    default=1.0,
                )

            # For optimization modes, reframe as savings potential
            is_emergency = event_type == "fire"
            if is_emergency:
                # Emergency scenario: show damage and evacuation
                evac_str = f"{evac_time:.0f}" if evac_time is not None else "N/A"
                return html.Div(
                    [
                        create_kpi_card(
                            title="Potential Damage",
                            value=f"€{total_damage:.0f}",
                            icon="mdi:alert-circle",
                        ),
                        create_kpi_card(
                            title="Evacuation Time",
                            value=evac_str,
                            unit="s" if evac_time else "",
                            icon="mdi:run-fast",
                        ),
                        create_kpi_card(
                            title="Peak Impact",
                            value=f"{peak_impact:.1f}",
                            icon="mdi:chart-bell-curve-cumulative",
                        ),
                        create_kpi_card(
                            title="Zones Affected",
                            value=str(len(zones_affected)),
                            icon="mdi:map-marker-alert-outline",
                        ),
                    ],
                    className="grid-4",
                )

            # Optimization mode: per-scenario ROI data
            roi = SCENARIO_ROI.get(event_type, {})
            invest = roi.get("invest", 0)

            # For optimization scenarios total_damage IS monthly savings
            monthly_savings = total_damage
            annual_savings = monthly_savings * 12
            payback = (
                f"{invest / monthly_savings:.0f}"
                if monthly_savings > 0 and invest > 0
                else "0"
            )

            kpi_grid = html.Div(
                [
                    create_kpi_card(
                        title="Monthly Savings",
                        value=f"€{monthly_savings:.0f}",
                        icon="mdi:piggy-bank-outline",
                    ),
                    create_kpi_card(
                        title="Investment",
                        value=f"€{invest:,}" if invest > 0 else "€0",
                        icon="mdi:cash-plus",
                    ),
                    create_kpi_card(
                        title="Payback",
                        value=payback if invest > 0 else "Immediate",
                        unit="months" if invest > 0 else "",
                        icon="mdi:calendar-clock",
                    ),
                    create_kpi_card(
                        title="Annual Savings",
                        value=f"€{annual_savings:.0f}",
                        icon="mdi:trending-up",
                    ),
                ],
                className="grid-4",
            )

            # Show PSO-optimized setpoint recommendations if available
            pso_recs = result_data.get("pso_recommendations")
            if pso_recs and event_type in _HVAC_SCENARIOS:
                rec_items = []
                for zone_id, rec in pso_recs.items():
                    zone_info = get_zone_by_id(zone_id)
                    zname = zone_info.name if zone_info else zone_id
                    imp = rec.get("improvement_pct", 0)
                    rec_items.append(
                        html.Div(
                            [
                                html.Span(
                                    zname,
                                    style={
                                        "fontWeight": 600,
                                        "fontSize": "13px",
                                        "color": TEXT_PRIMARY,
                                    },
                                ),
                                html.Span(
                                    f"{rec['temp_setpoint_c']}°C · "
                                    f"{rec['ventilation_ach']} ACH · "
                                    f"{imp:.0f}% better",
                                    style={
                                        "fontSize": "12px",
                                        "color": STATUS_HEALTHY,
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "padding": "6px 0",
                            },
                        )
                    )
                pso_card = html.Div(
                    [
                        html.Div(
                            [
                                DashIconify(
                                    icon="mdi:tune-vertical",
                                    width=16,
                                    color=ACCENT_BLUE,
                                ),
                                html.Span(
                                    "PSO-Optimized Setpoints",
                                    style={
                                        "fontWeight": 600,
                                        "fontSize": "14px",
                                        "color": TEXT_PRIMARY,
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "gap": "6px",
                                "alignItems": "center",
                                "marginBottom": "8px",
                            },
                        ),
                        *rec_items,
                    ],
                    className="card",
                    style={
                        "padding": "14px 16px",
                        "background": BG_CARD,
                        "borderRadius": CARD_RADIUS,
                        "boxShadow": CARD_SHADOW,
                        "marginTop": "12px",
                    },
                )
                return html.Div([kpi_grid, pso_card])

            return kpi_grid
        except Exception as exc:
            logger.error(f"Savings summary render error: {exc}")
            return empty_damage_summary()


# ═══════════════════════════════════════════════
# Callback 4: Affected Zones
# ═══════════════════════════════════════════════


def _register_affected_zones(app: object) -> None:
    """Register the callback that renders the affected zones list.

    Displays zone badges with severity indicators. The first zone
    (primary) gets a critical badge, others get warning badges.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("sim-affected-zones", "children"),
        Input("sim-result-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def update_affected_zones(
        result_data: dict | None,
        pathname: str | None,
    ) -> html.Div:
        """Build the affected zones card with severity badges.

        Args:
            result_data: Serialized SimulationResult dict from the store.
            pathname: Current page URL path.

        Returns:
            Dash html.Div containing a card with zone badges.
        """
        if not result_data:
            return empty_affected_zones()

        try:
            zones_affected = result_data.get("zones_affected", [])
            if not zones_affected:
                return empty_affected_zones()

            badge_items: list[html.Span] = []
            for i, zone_id in enumerate(zones_affected):
                zone_info = get_zone_by_id(zone_id)
                display_name = zone_info.name if zone_info else zone_id

                # First zone is the primary target — critical severity
                if i == 0:
                    badge_class = "status-badge critical"
                else:
                    badge_class = "status-badge warning"

                badge_items.append(
                    html.Span(
                        display_name,
                        className=badge_class,
                        style={
                            "display": "inline-block",
                            "margin": "4px",
                        },
                    )
                )

            return html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:map-marker-radius-outline",
                                width=18,
                                color=TEXT_SECONDARY,
                            ),
                            html.Span(
                                "Affected Zones",
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
                            "padding": "14px 16px",
                            "borderBottom": f"1px solid {ACCENT_BLUE}10",
                        },
                    ),
                    html.Div(
                        badge_items,
                        style={
                            "padding": "12px 16px",
                            "display": "flex",
                            "flexWrap": "wrap",
                            "gap": "4px",
                        },
                    ),
                ],
                className="card",
                style={
                    "background": BG_CARD,
                    "borderRadius": CARD_RADIUS,
                    "boxShadow": CARD_SHADOW,
                    "overflow": "hidden",
                },
            )
        except Exception as exc:
            logger.error(f"Affected zones render error: {exc}")
            return empty_affected_zones()
