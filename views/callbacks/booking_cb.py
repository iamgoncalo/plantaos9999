"""Smart Booking page callbacks.

Registers callbacks for the temporal intelligence engine: "Look Back" mode
retrieves historical energy/comfort/AFI metrics for a past booking window,
while "Look Forward" mode simulates projected temperature, CO2, energy cost,
and comfort for a future room reservation.
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate
from datetime import date, datetime, timedelta
from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
from config.theme import (
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from data.store import store
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card

try:
    from data.physical_ai_bridge import (
        RoomPhysicsState,
        simulate_room_physics,
    )

    HAS_PHYSICS = True
except ImportError:
    HAS_PHYSICS = False


def register_booking_callbacks(app: object) -> None:
    """Register all Smart Booking page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_booking_analysis(app)


# ═══════════════════════════════════════════════
# Callback: Booking Analysis
# ═══════════════════════════════════════════════


def _register_booking_analysis(app: object) -> None:
    """Register the main booking analysis callback.

    Handles both Look Back (historical) and Look Forward (simulation)
    modes. Produces KPI cards, a dual-axis physics chart, and a
    natural-language room recommendation.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("booking-kpi-grid", "children"),
        Output("booking-physics-chart", "figure"),
        Output("booking-recommendation", "children"),
        Input("booking-analyze-btn", "n_clicks"),
        State("booking-mode", "value"),
        State("booking-zone-selector", "value"),
        State("booking-date-picker", "date"),
        State("booking-time-start", "value"),
        State("booking-duration", "value"),
        State("booking-people", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def analyze_booking(
        n_clicks: int | None,
        mode: str | None,
        zone_id: str | None,
        selected_date: str | None,
        start_hour: int | None,
        duration: int | None,
        people: int | None,
        pathname: str | None,
    ) -> tuple[list, go.Figure, html.Div]:
        """Run booking analysis for the selected parameters.

        Args:
            n_clicks: Analyze button click count.
            mode: "past" for Look Back, "future" for Look Forward.
            zone_id: Selected zone identifier.
            selected_date: Date string from the date picker.
            start_hour: Start hour (6-22).
            duration: Duration in hours (1, 2, 4, 8).
            people: Number of occupants.
            pathname: Current page URL path.

        Returns:
            Tuple of (KPI card list, physics chart figure,
            recommendation div).
        """
        if pathname != "/booking":
            raise PreventUpdate

        if not n_clicks:
            raise PreventUpdate

        # Validate required inputs
        if not zone_id or not selected_date or start_hour is None:
            raise PreventUpdate

        duration = duration or 1
        people = people or 15

        try:
            booking_date = datetime.fromisoformat(str(selected_date)).date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid booking date: {selected_date}")
            raise PreventUpdate

        try:
            if mode == "future":
                return _analyze_forward(
                    zone_id, booking_date, start_hour, duration, people
                )
            else:
                return _analyze_backward(
                    zone_id, booking_date, start_hour, duration, people
                )
        except PreventUpdate:
            raise
        except Exception as exc:
            logger.warning(f"Booking analysis error: {exc}")
            return no_update, no_update, no_update


# ═══════════════════════════════════════════════
# Look Back: Historical Analysis
# ═══════════════════════════════════════════════


def _analyze_backward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Analyze a past booking window using historical data.

    Retrieves energy, comfort, and occupancy data for the specified
    zone and time window, then computes actual KPIs and plots
    historical temperature and CO2 traces.

    Args:
        zone_id: Zone identifier.
        booking_date: The date of the past booking.
        start_hour: Start hour of the booking window.
        duration: Duration in hours.
        people: Number of occupants (for Added Value calculation).

    Returns:
        Tuple of (KPI cards, physics chart, recommendation).
    """
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id

    start_dt = datetime.combine(
        booking_date, datetime.min.time().replace(hour=start_hour)
    )
    end_dt = start_dt + timedelta(hours=duration)

    # ── Fetch historical data ──────────────────
    energy_df = store.get_time_range("energy", start_dt, end_dt)
    comfort_df = store.get_time_range("comfort", start_dt, end_dt)
    occupancy_df = store.get_time_range("occupancy", start_dt, end_dt)

    # Filter to selected zone
    if energy_df is not None and not energy_df.empty and "zone_id" in energy_df.columns:
        energy_df = energy_df[energy_df["zone_id"] == zone_id]
    if (
        comfort_df is not None
        and not comfort_df.empty
        and "zone_id" in comfort_df.columns
    ):
        comfort_df = comfort_df[comfort_df["zone_id"] == zone_id]
    if (
        occupancy_df is not None
        and not occupancy_df.empty
        and "zone_id" in occupancy_df.columns
    ):
        occupancy_df = occupancy_df[occupancy_df["zone_id"] == zone_id]

    # ── Compute KPIs ──────────────────────────
    # Energy used
    energy_kwh = 0.0
    if (
        energy_df is not None
        and not energy_df.empty
        and "total_kwh" in energy_df.columns
    ):
        energy_kwh = float(energy_df["total_kwh"].sum())

    # Comfort index (average of temperature compliance + CO2 compliance)
    comfort_index = 0.0
    comfort_components = 0
    avg_temp = None
    avg_co2 = None

    if comfort_df is not None and not comfort_df.empty:
        if "temperature_c" in comfort_df.columns:
            avg_temp = float(comfort_df["temperature_c"].mean())
            # Score: 100 if within 20-24, decreasing outside
            temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
            temp_score = max(0.0, 100.0 - temp_dev * 15.0)
            comfort_index += temp_score
            comfort_components += 1
        if "co2_ppm" in comfort_df.columns:
            avg_co2 = float(comfort_df["co2_ppm"].mean())
            co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
            co2_score = max(0.0, 100.0 - co2_dev * 0.1)
            comfort_index += co2_score
            comfort_components += 1

    if comfort_components > 0:
        comfort_index = comfort_index / comfort_components
    else:
        comfort_index = 50.0

    # Freedom index approximation
    freedom_index = comfort_index * 0.85 + 15.0  # Simplified proxy

    # Added Value per Person = (freedom_index / 100) * avg_hourly_wage * hours * occupants
    avg_wage = DEFAULT_AFI_CONFIG.avg_hourly_wage
    added_value = (freedom_index / 100.0) * avg_wage * duration * people

    # ── Build KPI cards ────────────────────────
    kpis = [
        create_kpi_card(
            title="Energy Used",
            value=f"{energy_kwh:.1f}",
            unit="kWh",
            icon="mdi:flash",
        ),
        create_kpi_card(
            title="Comfort Index",
            value=f"{comfort_index:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            title="Added Value",
            value=f"{added_value:.0f}",
            unit="\u20ac",
            icon="mdi:currency-eur",
        ),
        create_kpi_card(
            title="Avg Freedom",
            value=f"{freedom_index:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    # ── Build physics chart ────────────────────
    fig = _build_historical_chart(comfort_df, start_dt, end_dt, zone_name)

    # ── Recommendation ─────────────────────────
    if comfort_index >= 75:
        status_color = STATUS_HEALTHY
        status_text = "Excellent"
        rec_text = (
            f"Historical analysis for {zone_name}: comfort conditions were "
            f"excellent during this {duration}h window. Average temperature "
            f"{avg_temp:.1f} \u00b0C, CO\u2082 {avg_co2:.0f} ppm. "
            f"Estimated added value: \u20ac{added_value:.0f} for {people} people."
            if avg_temp is not None and avg_co2 is not None
            else f"Historical analysis for {zone_name}: comfort conditions "
            f"were excellent during this {duration}h window."
        )
    elif comfort_index >= 50:
        status_color = STATUS_WARNING
        status_text = "Moderate"
        rec_text = (
            f"Historical analysis for {zone_name}: moderate comfort during "
            f"this {duration}h window. Consider reviewing HVAC schedules "
            f"for this time slot."
        )
    else:
        status_color = STATUS_CRITICAL
        status_text = "Poor"
        rec_text = (
            f"Historical analysis for {zone_name}: poor comfort conditions "
            f"detected. This time slot had significant deviations from "
            f"optimal ranges. Recommend choosing an alternative room or time."
        )

    recommendation = _build_recommendation(status_color, status_text, rec_text)

    return kpis, fig, recommendation


def _build_historical_chart(
    comfort_df: object,
    start_dt: datetime,
    end_dt: datetime,
    zone_name: str,
) -> go.Figure:
    """Build a dual-axis chart with historical temperature and CO2.

    Args:
        comfort_df: Comfort DataFrame (may be None or empty).
        start_dt: Window start datetime.
        end_dt: Window end datetime.
        zone_name: Display name for the zone.

    Returns:
        Plotly Figure with temperature on left axis and CO2 on right.
    """
    if comfort_df is None or comfort_df.empty:
        return empty_chart("No historical comfort data for this window")

    fig = go.Figure()

    # Temperature trace — left y-axis
    if "temperature_c" in comfort_df.columns and "timestamp" in comfort_df.columns:
        fig.add_trace(
            go.Scatter(
                x=comfort_df["timestamp"],
                y=comfort_df["temperature_c"],
                mode="lines",
                name="Temperature (\u00b0C)",
                line=dict(color=STATUS_CRITICAL, width=2),
                hovertemplate="%{x|%H:%M}<br>%{y:.1f} \u00b0C<extra></extra>",
            )
        )

    # CO2 trace — right y-axis
    if "co2_ppm" in comfort_df.columns and "timestamp" in comfort_df.columns:
        fig.add_trace(
            go.Scatter(
                x=comfort_df["timestamp"],
                y=comfort_df["co2_ppm"],
                mode="lines",
                name="CO\u2082 (ppm)",
                line=dict(color=STATUS_WARNING, width=2),
                yaxis="y2",
                hovertemplate="%{x|%H:%M}<br>%{y:.0f} ppm<extra></extra>",
            )
        )

    fig.update_layout(
        yaxis=dict(
            title="Temperature (\u00b0C)",
            titlefont=dict(color=STATUS_CRITICAL),
            tickfont=dict(color=STATUS_CRITICAL),
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            tickfont=dict(color=STATUS_WARNING),
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

    return apply_chart_theme(fig, f"Historical Comfort \u2014 {zone_name}", height=360)


# ═══════════════════════════════════════════════
# Look Forward: Future Projection
# ═══════════════════════════════════════════════


def _analyze_forward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Project future booking metrics using physics simulation.

    If the physical_ai_bridge module is available, uses
    simulate_room_physics() for high-fidelity projections. Otherwise
    falls back to a simplified thermal model.

    Args:
        zone_id: Zone identifier.
        booking_date: The date of the future booking.
        start_hour: Start hour of the booking window.
        duration: Duration in hours.
        people: Expected number of occupants.

    Returns:
        Tuple of (KPI cards, projection chart, recommendation).
    """
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    zone_area = zone.area_m2 if zone else 40.0
    zone_capacity = zone.capacity if zone else 30

    steps = duration * 4  # 15-minute intervals
    timestamps = [
        datetime.combine(
            booking_date,
            datetime.min.time().replace(hour=start_hour),
        )
        + timedelta(minutes=15 * i)
        for i in range(steps + 1)
    ]

    # ── Physics simulation ─────────────────────
    if HAS_PHYSICS:
        try:
            initial_state = RoomPhysicsState(
                temperature_c=DEFAULT_AFI_CONFIG.optimal_temperature_c,
                co2_ppm=DEFAULT_AFI_CONFIG.optimal_co2_ppm,
                occupant_count=people,
                room_area_m2=zone_area,
                ceiling_height_m=DEFAULT_AFI_CONFIG.ceiling_height_m,
            )
            sim_result = simulate_room_physics(
                initial_state,
                duration_hours=duration,
                step_minutes=15,
            )
            temps = [s.temperature_c for s in sim_result]
            co2s = [s.co2_ppm for s in sim_result]
            # Trim or pad to match timestamps length
            temps = (temps + [temps[-1]] * len(timestamps))[: len(timestamps)]
            co2s = (co2s + [co2s[-1]] * len(timestamps))[: len(timestamps)]
        except Exception as exc:
            logger.warning(f"Physics simulation failed, using fallback: {exc}")
            temps, co2s = _fallback_projection(people, zone_area, duration, steps)
    else:
        temps, co2s = _fallback_projection(people, zone_area, duration, steps)

    # ── Compute projected KPIs ─────────────────
    avg_temp = sum(temps) / len(temps)
    avg_co2 = sum(co2s) / len(co2s)
    peak_co2 = max(co2s)

    # Projected energy: HVAC load to maintain temperature
    temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
    hvac_load_kw = (
        DEFAULT_AFI_CONFIG.air_density
        * DEFAULT_AFI_CONFIG.air_specific_heat
        * zone_area
        * DEFAULT_AFI_CONFIG.ceiling_height_m
        * temp_dev
        / (3600 * DEFAULT_AFI_CONFIG.hvac_efficiency)
    )
    projected_energy = max(0.5, hvac_load_kw * duration + people * 0.05 * duration)

    # Comfort index
    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    predicted_comfort = (temp_score + co2_score) / 2.0

    # Freedom index
    projected_freedom = predicted_comfort * 0.85 + 15.0

    # Find optimal room (lowest projected distortion)
    optimal_room = _find_optimal_room(people, duration)

    # ── Build KPI cards ────────────────────────
    kpis = [
        create_kpi_card(
            title="Projected Energy",
            value=f"{projected_energy:.1f}",
            unit="kWh",
            icon="mdi:flash-outline",
        ),
        create_kpi_card(
            title="Predicted Comfort",
            value=f"{predicted_comfort:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            title="Optimal Room",
            value=optimal_room,
            icon="mdi:star-outline",
        ),
        create_kpi_card(
            title="Projected Freedom",
            value=f"{projected_freedom:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    # ── Build projection chart ─────────────────
    fig = _build_projection_chart(timestamps, temps, co2s, zone_name)

    # ── Recommendation ─────────────────────────
    occupancy_ratio = people / zone_capacity if zone_capacity > 0 else 1.0

    if predicted_comfort >= 75 and occupancy_ratio <= 0.85:
        status_color = STATUS_HEALTHY
        status_text = "Recommended"
        rec_text = (
            f"{zone_name} is an excellent choice for {people} people over "
            f"{duration}h. Projected comfort {predicted_comfort:.0f}/100, "
            f"peak CO\u2082 {peak_co2:.0f} ppm, energy cost "
            f"\u20ac{projected_energy * DEFAULT_AFI_CONFIG.cost_per_kwh:.2f}."
        )
    elif predicted_comfort >= 50 or occupancy_ratio <= 1.0:
        status_color = STATUS_WARNING
        status_text = "Acceptable"
        rec_text = (
            f"{zone_name} can accommodate {people} people but conditions "
            f"may degrade after {duration // 2 + 1}h. Consider "
            f"{optimal_room} for better comfort. Projected peak CO\u2082 "
            f"{peak_co2:.0f} ppm."
        )
    else:
        status_color = STATUS_CRITICAL
        status_text = "Not Recommended"
        rec_text = (
            f"{zone_name} is not suitable for {people} people over "
            f"{duration}h. Capacity ratio {occupancy_ratio:.0%} exceeds "
            f"safe limits. Strongly recommend {optimal_room} instead."
        )

    recommendation = _build_recommendation(status_color, status_text, rec_text)

    return kpis, fig, recommendation


def _fallback_projection(
    people: int,
    area_m2: float,
    duration: int,
    steps: int,
) -> tuple[list[float], list[float]]:
    """Generate simplified temperature and CO2 projections.

    Uses basic thermal and CO2 accumulation models when the
    physical_ai_bridge module is not available.

    Args:
        people: Number of occupants.
        area_m2: Room area in square meters.
        duration: Booking duration in hours.
        steps: Number of 15-minute intervals.

    Returns:
        Tuple of (temperature list, CO2 list) with steps+1 entries.
    """
    base_temp = DEFAULT_AFI_CONFIG.optimal_temperature_c
    base_co2 = DEFAULT_AFI_CONFIG.optimal_co2_ppm

    # Each person adds ~80W heat and ~20 L/h CO2
    heat_per_person_kw = 0.08
    co2_per_person_ppm_per_step = 5.0  # per 15-min step

    # Room thermal mass dampens temperature rise
    thermal_mass = area_m2 * DEFAULT_AFI_CONFIG.ceiling_height_m * 1.2
    # Ventilation provides CO2 removal
    ventilation_decay = 0.02  # per step

    temps = [base_temp]
    co2s = [base_co2]

    for i in range(steps):
        # Temperature: rises from body heat, HVAC tries to compensate
        heat_input = people * heat_per_person_kw * 0.25  # per 15 min
        temp_rise = heat_input / thermal_mass * 100
        hvac_correction = (temps[-1] - base_temp) * 0.3
        new_temp = temps[-1] + temp_rise - hvac_correction
        temps.append(round(new_temp, 2))

        # CO2: rises from people, decays from ventilation
        co2_input = people * co2_per_person_ppm_per_step
        co2_removal = (co2s[-1] - 400) * ventilation_decay
        new_co2 = co2s[-1] + co2_input - co2_removal
        co2s.append(round(max(400.0, new_co2), 1))

    return temps, co2s


def _build_projection_chart(
    timestamps: list[datetime],
    temps: list[float],
    co2s: list[float],
    zone_name: str,
) -> go.Figure:
    """Build a dual-axis chart with projected temperature and CO2.

    Args:
        timestamps: List of datetime values for the x-axis.
        temps: Projected temperature values (\u00b0C).
        co2s: Projected CO2 values (ppm).
        zone_name: Display name for the zone.

    Returns:
        Plotly Figure with temperature on left axis and CO2 on right.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=temps,
            mode="lines",
            name="Projected Temp (\u00b0C)",
            line=dict(color=STATUS_CRITICAL, width=2),
            hovertemplate="%{x|%H:%M}<br>%{y:.1f} \u00b0C<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=co2s,
            mode="lines",
            name="Projected CO\u2082 (ppm)",
            line=dict(color=STATUS_WARNING, width=2),
            yaxis="y2",
            hovertemplate="%{x|%H:%M}<br>%{y:.0f} ppm<extra></extra>",
        )
    )

    fig.update_layout(
        yaxis=dict(
            title="Temperature (\u00b0C)",
            titlefont=dict(color=STATUS_CRITICAL),
            tickfont=dict(color=STATUS_CRITICAL),
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            tickfont=dict(color=STATUS_WARNING),
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

    return apply_chart_theme(fig, f"Projected Comfort \u2014 {zone_name}", height=360)


def _find_optimal_room(people: int, duration: int) -> str:
    """Find the best room for the given occupant count and duration.

    Selects the monitored zone with the smallest capacity that still
    fits the requested number of people, minimizing overcrowding
    distortion.

    Args:
        people: Expected number of occupants.
        duration: Booking duration in hours.

    Returns:
        Display name of the optimal zone.
    """
    candidates = []
    for zone in get_monitored_zones():
        if zone.capacity >= people:
            # Distortion: lower is better (closer fit = less wasted space)
            distortion = (zone.capacity - people) / zone.capacity
            candidates.append((distortion, zone))

    if not candidates:
        # No single room fits — pick the largest
        all_zones = get_monitored_zones()
        if all_zones:
            largest = max(all_zones, key=lambda z: z.capacity)
            return largest.name
        return "N/A"

    # Sort by distortion (lowest = best fit)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].name


def _build_recommendation(
    status_color: str,
    status_text: str,
    rec_text: str,
) -> html.Div:
    """Build the recommendation card with status badge and text.

    Args:
        status_color: Hex color for the status indicator.
        status_text: Short status label (e.g., "Recommended").
        rec_text: Full recommendation description.

    Returns:
        Dash html.Div containing the styled recommendation card.
    """
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        style={
                            "width": "10px",
                            "height": "10px",
                            "borderRadius": "50%",
                            "background": status_color,
                            "display": "inline-block",
                            "flexShrink": 0,
                        },
                    ),
                    html.Span(
                        status_text,
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
                    "gap": "10px",
                    "marginBottom": "8px",
                },
            ),
            html.P(
                rec_text,
                style={
                    "margin": 0,
                    "color": TEXT_SECONDARY,
                    "fontSize": "13px",
                    "lineHeight": "1.5",
                },
            ),
        ],
        style={
            "padding": "16px 20px",
        },
    )
