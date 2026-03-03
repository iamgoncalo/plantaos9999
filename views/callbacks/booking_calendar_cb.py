"""Booking calendar and room-analysis callbacks.

Registers callbacks for today's bookings timeline and room analysis
(historical look-back and future projections).
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate
from datetime import date, datetime, timedelta
from loguru import logger

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
from utils.booking_helpers import compute_backward_analysis, compute_forward_analysis
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback


def register_booking_calendar_callbacks(app: object) -> None:
    """Register calendar and analysis callbacks."""
    _register_calendar_view(app)
    _register_booking_analysis(app)


def _register_calendar_view(app: object) -> None:
    """Render today's bookings as a timeline chart."""

    @app.callback(
        Output("booking-calendar-chart", "figure"),
        Input("bookings-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_calendar(bookings: list | None, pathname: str | None) -> go.Figure:
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
            name = b.get("zone_name", b.get("zone_id", "Room"))
            sh, dur, ppl = (
                b.get("start_hour", 9),
                b.get("duration", 1),
                b.get("people", 0),
            )
            fig.add_trace(
                go.Bar(
                    x=[dur],
                    y=[name],
                    base=[sh],
                    orientation="h",
                    marker=dict(color=colors[i % len(colors)], cornerradius=4),
                    text=f"{sh:02d}:00-{sh + dur:02d}:00 ({ppl}p)",
                    textposition="inside",
                    textfont=dict(size=11, color="#FFFFFF"),
                    hovertemplate=f"<b>{name}</b><br>{sh:02d}:00 - {sh + dur:02d}:00<br>{ppl} people<extra></extra>",
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
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=180)
    return apply_chart_theme(fig, "", height=180)


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
        n_clicks,
        mode,
        zone_id,
        selected_date,
        start_hour,
        duration,
        people,
        pathname,
    ) -> tuple[list, go.Figure, html.Div]:
        """Run booking analysis for the selected parameters."""
        if pathname != "/booking" or not n_clicks:
            return no_update, no_update, no_update
        if not zone_id or not selected_date or start_hour is None:
            return no_update, no_update, no_update
        duration, people = duration or 1, people or 15
        try:
            bdate = datetime.fromisoformat(str(selected_date)).date()
        except (ValueError, TypeError):
            raise PreventUpdate
        try:
            if mode == "future":
                return _analyze_forward(zone_id, bdate, start_hour, duration, people)
            return _analyze_backward(zone_id, bdate, start_hour, duration, people)
        except PreventUpdate:
            raise
        except Exception as exc:
            logger.warning(f"Booking analysis error: {exc}")
            return no_update, no_update, no_update


def _analyze_backward(zone_id, bdate, start_hour, duration, people):
    """Analyze a past booking window using historical data."""
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    start_dt = datetime.combine(bdate, datetime.min.time().replace(hour=start_hour))
    end_dt = start_dt + timedelta(hours=duration)
    energy_df = store.get_time_range("energy", start_dt, end_dt)
    comfort_df = store.get_time_range("comfort", start_dt, end_dt)
    for df in [energy_df, comfort_df]:
        if df is not None and not df.empty:
            for col in df.select_dtypes(include=["number"]).columns:
                df[col] = df[col].ffill().bfill().fillna(0)
    if energy_df is not None and not energy_df.empty and "zone_id" in energy_df.columns:
        energy_df = energy_df[energy_df["zone_id"] == zone_id]
    if (
        comfort_df is not None
        and not comfort_df.empty
        and "zone_id" in comfort_df.columns
    ):
        comfort_df = comfort_df[comfort_df["zone_id"] == zone_id]

    d = compute_backward_analysis(energy_df, comfort_df, duration, people)
    kpis = [
        create_kpi_card(
            "Energy Used", f"{d['energy_kwh']:.1f}", unit="kWh", icon="mdi:flash"
        ),
        create_kpi_card(
            "Comfort Index",
            f"{d['comfort_index']:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            "Added Value",
            f"{d['added_value']:.0f}",
            unit="\u20ac",
            icon="mdi:currency-eur",
        ),
        create_kpi_card(
            "Zone Performance",
            f"{d['performance']:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]
    fig = _build_dual_chart(comfort_df, zone_name, "Historical Comfort")
    ci = d["comfort_index"]
    if ci >= 75:
        sc, st = STATUS_HEALTHY, "Excellent"
        rt = f"Historical analysis for {zone_name}: excellent comfort during this {duration}h window."
        if d["avg_temp"] is not None and d["avg_co2"] is not None:
            rt += f" Avg temperature {d['avg_temp']:.1f} \u00b0C, CO\u2082 {d['avg_co2']:.0f} ppm."
    elif ci >= 50:
        sc, st = STATUS_WARNING, "Moderate"
        rt = f"Historical analysis for {zone_name}: moderate comfort. Consider reviewing HVAC schedules."
    else:
        sc, st = STATUS_CRITICAL, "Poor"
        rt = f"Historical analysis for {zone_name}: poor comfort. Recommend alternative room or time."
    return kpis, fig, _build_recommendation(sc, st, rt)


def _analyze_forward(zone_id, bdate, start_hour, duration, people):
    """Project future booking metrics."""
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    zone_area = zone.area_m2 if zone else 40.0
    zone_cap = zone.capacity if zone else 30
    steps = duration * 4
    timestamps = [
        datetime.combine(bdate, datetime.min.time().replace(hour=start_hour))
        + timedelta(minutes=15 * i)
        for i in range(steps + 1)
    ]
    d = compute_forward_analysis(zone_id, zone_area, zone_cap, people, duration)
    kpis = [
        create_kpi_card(
            "Projected Energy",
            f"{d['projected_energy']:.1f}",
            unit="kWh",
            icon="mdi:flash-outline",
        ),
        create_kpi_card(
            "Predicted Comfort",
            f"{d['predicted_comfort']:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card("Optimal Room", d["optimal_room"], icon="mdi:star-outline"),
        create_kpi_card(
            "Zone Performance",
            f"{d['projected_perf']:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]
    fig = _build_projection_chart(timestamps, d["temps"], d["co2s"], zone_name)
    pc = d["predicted_comfort"]
    if pc >= 75 and d["occ_ratio"] <= 0.85:
        sc, st = STATUS_HEALTHY, "Recommended"
        rt = (
            f"{zone_name} is excellent for {people} people over {duration}h. "
            f"Comfort {pc:.0f}/100, peak CO\u2082 {d['peak_co2']:.0f} ppm, cost \u20ac{d['energy_cost']:.2f}."
        )
    elif pc >= 50 or d["occ_ratio"] <= 1.0:
        sc, st = STATUS_WARNING, "Acceptable"
        rt = f"{zone_name} can accommodate {people} people but conditions may degrade. Consider {d['optimal_room']}."
    else:
        sc, st = STATUS_CRITICAL, "Not Recommended"
        rt = f"{zone_name} is not suitable for {people} people over {duration}h. Recommend {d['optimal_room']}."
    return kpis, fig, _build_recommendation(sc, st, rt)


def _build_dual_chart(comfort_df, zone_name, prefix):
    """Build dual-axis chart with historical temperature and CO2."""
    if comfort_df is None or comfort_df.empty:
        return empty_chart("No historical comfort data for this window")
    fig = go.Figure()
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
            title="Temperature (\u00b0C)", titlefont=dict(color=STATUS_CRITICAL)
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
    )
    return apply_chart_theme(fig, f"{prefix} \u2014 {zone_name}", height=360)


def _build_projection_chart(timestamps, temps, co2s, zone_name):
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
            title="Temperature (\u00b0C)", titlefont=dict(color=STATUS_CRITICAL)
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
    )
    return apply_chart_theme(fig, f"Projected Comfort \u2014 {zone_name}", height=360)


def _build_recommendation(status_color, status_text, rec_text):
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
                        }
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
