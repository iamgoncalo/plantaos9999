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
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from core.simulation import SimulationEvent, SimulationResult, simulate_event
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card


def register_simulation_callbacks(app: object) -> None:
    """Register all simulation page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_trigger(app)
    _register_timeline(app)
    _register_damage_summary(app)
    _register_affected_zones(app)


# ═══════════════════════════════════════════════
# Callback 1: Trigger Simulation
# ═══════════════════════════════════════════════


def _register_trigger(app: object) -> None:
    """Register the callback that triggers a simulation run.

    Listens for button clicks on sim-trigger-btn and creates a
    SimulationEvent from the form state, runs simulate_event(),
    and stores the serialized result in sim-result-store.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("sim-result-store", "data"),
        Input("sim-trigger-btn", "n_clicks"),
        State("sim-event-type", "value"),
        State("sim-zone-selector", "value"),
        State("sim-intensity-slider", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def trigger_simulation(
        n_clicks: int | None,
        event_type: str | None,
        zone_id: str | None,
        intensity: float | None,
        pathname: str | None,
    ) -> dict | object:
        """Run the simulation engine and store the result.

        Args:
            n_clicks: Button click count.
            event_type: Selected event type string.
            zone_id: Selected zone identifier.
            intensity: Intensity slider value (0.1-1.0).
            pathname: Current page URL path.

        Returns:
            Serialized SimulationResult dict, or no_update if skipped.
        """
        if pathname != "/simulation":
            return no_update

        if not n_clicks or not event_type or not zone_id:
            return no_update

        try:
            event = SimulationEvent(
                event_type=event_type,
                zone_id=zone_id,
                intensity=intensity or 0.8,
            )
            result: SimulationResult = simulate_event(
                event, duration_hours=24, step_minutes=15
            )
            logger.info(
                f"Simulation complete: {event_type} in {zone_id}, "
                f"damage=€{result.total_financial_damage_eur:.2f}"
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            logger.error(f"Simulation trigger error: {exc}")
            return no_update


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
    """Register the callback that renders the damage summary KPI cards.

    Shows four cards: Total Damage, Evacuation Time, Peak Distortion,
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
    def update_damage_summary(
        result_data: dict | None,
        pathname: str | None,
    ) -> html.Div:
        """Build damage summary KPI cards from simulation result.

        Args:
            result_data: Serialized SimulationResult dict from the store.
            pathname: Current page URL path.

        Returns:
            Dash html.Div containing four KPI cards in a grid-4 layout.
        """
        if not result_data:
            return _empty_damage_summary()

        try:
            total_damage = result_data.get("total_financial_damage_eur", 0.0)
            evac_time = result_data.get("evacuation_time_seconds")
            zones_affected = result_data.get("zones_affected", [])
            timeline = result_data.get("timeline", [])

            # Peak distortion from timeline steps
            peak_distortion = 1.0
            if timeline:
                peak_distortion = max(
                    (step.get("distortion", 1.0) for step in timeline),
                    default=1.0,
                )

            # Format evacuation time
            evac_str = f"{evac_time:.0f}" if evac_time is not None else "N/A"
            evac_unit = "s" if evac_time is not None else ""

            return html.Div(
                [
                    create_kpi_card(
                        title="Total Damage",
                        value=f"€{total_damage:.0f}",
                        icon="mdi:currency-eur",
                    ),
                    create_kpi_card(
                        title="Evacuation Time",
                        value=evac_str,
                        unit=evac_unit,
                        icon="mdi:run-fast",
                    ),
                    create_kpi_card(
                        title="Peak Distortion",
                        value=f"{peak_distortion:.1f}",
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
        except Exception as exc:
            logger.error(f"Damage summary render error: {exc}")
            return _empty_damage_summary()


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
            return _empty_affected_zones()

        try:
            zones_affected = result_data.get("zones_affected", [])
            if not zones_affected:
                return _empty_affected_zones()

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
            return _empty_affected_zones()


# ═══════════════════════════════════════════════
# Private Helpers
# ═══════════════════════════════════════════════


def _empty_damage_summary() -> html.Div:
    """Return placeholder KPI cards for the damage summary.

    Returns:
        Dash html.Div with placeholder KPI cards showing '--' values.
    """
    return html.Div(
        [
            create_kpi_card(
                title="Total Damage",
                value="--",
                unit="€",
                icon="mdi:currency-eur",
            ),
            create_kpi_card(
                title="Evacuation Time",
                value="--",
                unit="s",
                icon="mdi:run-fast",
            ),
            create_kpi_card(
                title="Peak Distortion",
                value="--",
                icon="mdi:chart-bell-curve-cumulative",
            ),
            create_kpi_card(
                title="Zones Affected",
                value="--",
                icon="mdi:map-marker-alert-outline",
            ),
        ],
        className="grid-4",
    )


def _empty_affected_zones() -> html.Div:
    """Return placeholder for the affected zones section.

    Returns:
        Dash html.Div with empty state message.
    """
    return html.Div(
        html.Div(
            [
                DashIconify(
                    icon="mdi:information-outline",
                    width=20,
                    color=TEXT_TERTIARY,
                ),
                html.Span(
                    "Run a simulation to see affected zones and cascade effects.",
                    style={
                        "color": TEXT_TERTIARY,
                        "fontSize": "13px",
                    },
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "8px",
                "padding": "16px 20px",
            },
        ),
        className="card",
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
        },
    )
