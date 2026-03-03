"""Booking calendar and room-analysis callbacks.

Registers callbacks for:
- Weekly calendar rendering (today's bookings as a timeline)
- Room analysis: historical look-back and future projections
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate
from datetime import date, datetime, timedelta
from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from data.store import store
from utils.booking_helpers import (
    fallback_projection,
    find_optimal_room,
)
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback

try:
    from data.physical_ai_bridge import (
        RoomPhysicsState,
        simulate_room_physics,
    )

    HAS_PHYSICS = True
except ImportError:
    HAS_PHYSICS = False


def register_booking_calendar_callbacks(app: object) -> None:
    """Register calendar and analysis callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_calendar_view(app)
    _register_booking_analysis(app)


# ===================================================
# Calendar View
# ===================================================


def _register_calendar_view(app: object) -> None:
    """Render today's bookings as a timeline chart."""

    @app.callback(
        Output("booking-calendar-chart", "figure"),
        Input("bookings-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_calendar(
        bookings: list | None,
        pathname: str | None,
    ) -> go.Figure:
        """Build a timeline chart of today's bookings."""
        if pathname != "/booking":
            return no_update

        bookings = bookings or []
        today_str = str(date.today())
        today_bookings = [b for b in bookings if b.get("date") == today_str]

        if not today_bookings:
            return _empty_calendar()

        fig = go.Figure()
        colors = [
            ACCENT_BLUE,
            STATUS_HEALTHY,
            STATUS_WARNING,
            "#5AC8FA",
            "#AF52DE",
            "#FF2D55",
        ]

        for i, b in enumerate(today_bookings):
            zone_name = b.get("zone_name", b.get("zone_id", "Room"))
            start_h = b.get("start_hour", 9)
            dur = b.get("duration", 1)
            people = b.get("people", 0)

            fig.add_trace(
                go.Bar(
                    x=[dur],
                    y=[zone_name],
                    base=[start_h],
                    orientation="h",
                    marker=dict(
                        color=colors[i % len(colors)],
                        cornerradius=4,
                    ),
                    text=(f"{start_h:02d}:00-{start_h + dur:02d}:00 ({people}p)"),
                    textposition="inside",
                    textfont=dict(size=11, color="#FFFFFF"),
                    hovertemplate=(
                        f"<b>{zone_name}</b><br>"
                        f"{start_h:02d}:00 - {start_h + dur:02d}:00<br>"
                        f"{people} people<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

        fig.update_layout(
            xaxis=dict(
                title="Hour",
                range=[6, 22],
                dtick=2,
                tickvals=list(range(6, 23, 2)),
                ticktext=[f"{h:02d}:00" for h in range(6, 23, 2)],
            ),
            yaxis=dict(title=""),
            barmode="overlay",
            height=180,
        )

        return apply_chart_theme(fig, "", height=180)


def _empty_calendar() -> go.Figure:
    """Return an empty calendar chart with placeholder message."""
    fig = go.Figure()
    fig.add_annotation(
        text="No bookings for today. Find a room above.",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color=TEXT_TERTIARY),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=180,
    )
    return apply_chart_theme(fig, "", height=180)


# ===================================================
# Room Analysis (Analyze Tab)
# ===================================================


def _register_booking_analysis(app: object) -> None:
    """Register the room analysis callback (Look Back / Look Forward)."""

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
    @safe_callback
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
        """Run booking analysis for the selected parameters."""
        if pathname != "/booking":
            return no_update, no_update, no_update
        if not n_clicks or not zone_id or not selected_date:
            return no_update, no_update, no_update
        if start_hour is None:
            return no_update, no_update, no_update

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
            return _analyze_backward(
                zone_id, booking_date, start_hour, duration, people
            )
        except PreventUpdate:
            raise
        except Exception as exc:
            logger.warning(f"Booking analysis error: {exc}")
            return no_update, no_update, no_update


def _analyze_backward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Analyze a past booking window using historical data."""
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id

    start_dt = datetime.combine(
        booking_date, datetime.min.time().replace(hour=start_hour)
    )
    end_dt = start_dt + timedelta(hours=duration)

    energy_df = store.get_time_range("energy", start_dt, end_dt)
    comfort_df = store.get_time_range("comfort", start_dt, end_dt)

    for df in [energy_df, comfort_df]:
        if df is not None and not df.empty:
            for col in df.select_dtypes(include=["number"]).columns:
                df[col] = df[col].ffill().bfill().fillna(0)

    if energy_df is not None and not energy_df.empty:
        if "zone_id" in energy_df.columns:
            energy_df = energy_df[energy_df["zone_id"] == zone_id]
    if comfort_df is not None and not comfort_df.empty:
        if "zone_id" in comfort_df.columns:
            comfort_df = comfort_df[comfort_df["zone_id"] == zone_id]

    energy_kwh = 0.0
    if energy_df is not None and not energy_df.empty:
        if "total_kwh" in energy_df.columns:
            energy_kwh = float(energy_df["total_kwh"].sum())

    comfort_index = 50.0
    avg_temp, avg_co2 = None, None

    if comfort_df is not None and not comfort_df.empty:
        scores = []
        if "temperature_c" in comfort_df.columns:
            avg_temp = float(comfort_df["temperature_c"].mean())
            dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
            scores.append(max(0.0, 100.0 - dev * 15.0))
        if "co2_ppm" in comfort_df.columns:
            avg_co2 = float(comfort_df["co2_ppm"].mean())
            dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
            scores.append(max(0.0, 100.0 - dev * 0.1))
        if scores:
            comfort_index = sum(scores) / len(scores)

    performance = comfort_index * 0.85 + 15.0
    avg_wage = DEFAULT_AFI_CONFIG.avg_hourly_wage
    added_value = (performance / 100.0) * avg_wage * duration * people

    kpis = [
        create_kpi_card(
            "Energy Used",
            f"{energy_kwh:.1f}",
            unit="kWh",
            icon="mdi:flash",
        ),
        create_kpi_card(
            "Comfort Index",
            f"{comfort_index:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            "Added Value",
            f"{added_value:.0f}",
            unit="\u20ac",
            icon="mdi:currency-eur",
        ),
        create_kpi_card(
            "Zone Performance",
            f"{performance:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    fig = _build_historical_chart(comfort_df, zone_name)

    if comfort_index >= 75:
        sc, st = STATUS_HEALTHY, "Excellent"
        rt = (
            f"Historical analysis for {zone_name}: comfort conditions were "
            f"excellent during this {duration}h window."
        )
        if avg_temp is not None and avg_co2 is not None:
            rt += (
                f" Average temperature {avg_temp:.1f} \u00b0C, "
                f"CO\u2082 {avg_co2:.0f} ppm. "
                f"Estimated added value: \u20ac{added_value:.0f} "
                f"for {people} people."
            )
    elif comfort_index >= 50:
        sc, st = STATUS_WARNING, "Moderate"
        rt = (
            f"Historical analysis for {zone_name}: moderate comfort during "
            f"this {duration}h window. Consider reviewing HVAC schedules."
        )
    else:
        sc, st = STATUS_CRITICAL, "Poor"
        rt = (
            f"Historical analysis for {zone_name}: poor comfort conditions. "
            f"Recommend choosing an alternative room or time."
        )

    return kpis, fig, _build_recommendation(sc, st, rt)


def _analyze_forward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Project future booking metrics using physics simulation."""
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    zone_area = zone.area_m2 if zone else 40.0
    zone_capacity = zone.capacity if zone else 30

    steps = duration * 4
    timestamps = [
        datetime.combine(
            booking_date,
            datetime.min.time().replace(hour=start_hour),
        )
        + timedelta(minutes=15 * i)
        for i in range(steps + 1)
    ]

    if HAS_PHYSICS:
        try:
            initial_state = RoomPhysicsState(
                zone_id=zone_id,
                temperature_c=DEFAULT_AFI_CONFIG.optimal_temperature_c,
                co2_ppm=DEFAULT_AFI_CONFIG.optimal_co2_ppm,
                humidity_pct=50.0,
                occupant_count=people,
                hvac_power_w=2000.0,
                ventilation_ach=2.0,
            )
            sim_result = simulate_room_physics(
                initial_state,
                area_m2=zone_area,
                duration_minutes=duration * 60,
                step_minutes=15,
            )
            temps = [s.temperature_c for s in sim_result]
            co2s = [s.co2_ppm for s in sim_result]
            temps = (temps + [temps[-1]] * len(timestamps))[: len(timestamps)]
            co2s = (co2s + [co2s[-1]] * len(timestamps))[: len(timestamps)]
        except Exception as exc:
            logger.warning(f"Physics simulation failed: {exc}")
            temps, co2s = fallback_projection(people, zone_area, duration, steps)
    else:
        temps, co2s = fallback_projection(people, zone_area, duration, steps)

    avg_temp = sum(temps) / len(temps)
    avg_co2 = sum(co2s) / len(co2s)
    peak_co2 = max(co2s)

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

    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    predicted_comfort = (temp_score + co2_score) / 2.0
    projected_perf = predicted_comfort * 0.85 + 15.0

    optimal_room = find_optimal_room(people)

    kpis = [
        create_kpi_card(
            "Projected Energy",
            f"{projected_energy:.1f}",
            unit="kWh",
            icon="mdi:flash-outline",
        ),
        create_kpi_card(
            "Predicted Comfort",
            f"{predicted_comfort:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            "Optimal Room",
            optimal_room,
            icon="mdi:star-outline",
        ),
        create_kpi_card(
            "Zone Performance",
            f"{projected_perf:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    fig = _build_projection_chart(timestamps, temps, co2s, zone_name)

    occ_ratio = people / zone_capacity if zone_capacity > 0 else 1.0
    cost = projected_energy * DEFAULT_AFI_CONFIG.cost_per_kwh

    if predicted_comfort >= 75 and occ_ratio <= 0.85:
        sc, st = STATUS_HEALTHY, "Recommended"
        rt = (
            f"{zone_name} is an excellent choice for {people} people over "
            f"{duration}h. Projected comfort {predicted_comfort:.0f}/100, "
            f"peak CO\u2082 {peak_co2:.0f} ppm, energy cost "
            f"\u20ac{cost:.2f}."
        )
    elif predicted_comfort >= 50 or occ_ratio <= 1.0:
        sc, st = STATUS_WARNING, "Acceptable"
        rt = (
            f"{zone_name} can accommodate {people} people but conditions "
            f"may degrade. Consider {optimal_room} for better comfort."
        )
    else:
        sc, st = STATUS_CRITICAL, "Not Recommended"
        rt = (
            f"{zone_name} is not suitable for {people} people over "
            f"{duration}h. Strongly recommend {optimal_room} instead."
        )

    return kpis, fig, _build_recommendation(sc, st, rt)


# ===================================================
# Chart Builders
# ===================================================


def _build_historical_chart(
    comfort_df: object,
    zone_name: str,
) -> go.Figure:
    """Build dual-axis chart with historical temperature and CO2."""
    if comfort_df is None or comfort_df.empty:
        return empty_chart("No historical comfort data for this window")

    fig = go.Figure()

    if "temperature_c" in comfort_df.columns:
        if "timestamp" in comfort_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=comfort_df["timestamp"],
                    y=comfort_df["temperature_c"],
                    mode="lines",
                    name="Temperature (\u00b0C)",
                    line=dict(color=STATUS_CRITICAL, width=2),
                    hovertemplate=("%{x|%H:%M}<br>%{y:.1f} \u00b0C<extra></extra>"),
                )
            )

    if "co2_ppm" in comfort_df.columns:
        if "timestamp" in comfort_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=comfort_df["timestamp"],
                    y=comfort_df["co2_ppm"],
                    mode="lines",
                    name="CO\u2082 (ppm)",
                    line=dict(color=STATUS_WARNING, width=2),
                    yaxis="y2",
                    hovertemplate=("%{x|%H:%M}<br>%{y:.0f} ppm<extra></extra>"),
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

    title = f"Historical Comfort \u2014 {zone_name}"
    return apply_chart_theme(fig, title, height=360)


def _build_projection_chart(
    timestamps: list[datetime],
    temps: list[float],
    co2s: list[float],
    zone_name: str,
) -> go.Figure:
    """Build dual-axis chart with projected temperature and CO2."""
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

    title = f"Projected Comfort \u2014 {zone_name}"
    return apply_chart_theme(fig, title, height=360)


def _build_recommendation(
    status_color: str,
    status_text: str,
    rec_text: str,
) -> html.Div:
    """Build the recommendation card with status badge and text."""
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
        style={"padding": "16px 20px"},
    )
