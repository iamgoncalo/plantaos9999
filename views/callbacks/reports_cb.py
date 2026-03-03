"""Reports page callbacks.

Registers callbacks for KPIs and four charts on the financial reports page.
Data flows from the AFI engine through period-based aggregation to Plotly figures.
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, State, no_update
from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    STATUS_CRITICAL,
    STATUS_WARNING,
)
from core.afi_engine import compute_financial_bleed
from data.store import store
from utils.time_utils import get_period_range
from views.charts import TIME_RANGE_MAP, apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card


# ── Period → hours mapping ────────────────────
_PERIOD_HOURS: dict[str, float] = {
    "today": 24.0,
    "7d": 168.0,
    "30d": 720.0,
}


def register_reports_callbacks(app: object) -> None:
    """Register all reports page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_reports_kpis(app)
    _register_breakdown_pie(app)
    _register_trend_line(app)
    _register_zone_ranking(app)
    _register_savings_chart(app)


def _register_reports_kpis(app: object) -> None:
    """Update financial KPI cards from AFI engine bleed data."""

    @app.callback(
        Output("reports-kpi-grid", "children"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    def update_reports_kpis(_n: int, period: str, pathname: str | None) -> list:
        if pathname != "/reports":
            return no_update

        empty = [
            create_kpi_card("Total Energy Cost", "—", unit="€", icon="mdi:flash"),
            create_kpi_card(
                "Human Capital Loss", "—", unit="€", icon="mdi:account-group"
            ),
            create_kpi_card(
                "Window Penalties", "—", unit="€", icon="mdi:window-open-variant"
            ),
            create_kpi_card(
                "Net Savings", "—", unit="€", icon="mdi:piggy-bank-outline"
            ),
        ]

        try:
            hours = _PERIOD_HOURS.get(period, 24.0)
            zones = get_monitored_zones()
            if not zones:
                return empty

            total_energy = 0.0
            total_human = 0.0
            total_window = 0.0

            for zone in zones:
                bleed = compute_financial_bleed(zone.id)
                total_energy += bleed.energy_cost_eur_hr * hours
                total_human += bleed.human_capital_loss_eur_hr * hours
                total_window += bleed.open_window_penalty_eur_hr * hours

            total_cost = total_energy + total_human + total_window

            # Estimate baseline cost (10% higher than actual as savings proxy)
            baseline_cost = total_cost * 1.10
            net_savings = baseline_cost - total_cost

            return [
                create_kpi_card(
                    "Total Energy Cost",
                    f"{total_energy:.0f}"
                    if total_energy >= 1
                    else f"{total_energy:.2f}",
                    unit="€",
                    icon="mdi:flash",
                ),
                create_kpi_card(
                    "Human Capital Loss",
                    f"{total_human:.0f}" if total_human >= 1 else f"{total_human:.2f}",
                    unit="€",
                    icon="mdi:account-group",
                ),
                create_kpi_card(
                    "Window Penalties",
                    f"{total_window:.0f}"
                    if total_window >= 1
                    else f"{total_window:.2f}",
                    unit="€",
                    icon="mdi:window-open-variant",
                ),
                create_kpi_card(
                    "Net Savings",
                    f"{net_savings:+.0f}"
                    if abs(net_savings) >= 1
                    else f"{net_savings:+.2f}",
                    unit="€",
                    trend=((net_savings / baseline_cost) * 100)
                    if baseline_cost > 0
                    else None,
                    icon="mdi:piggy-bank-outline",
                ),
            ]
        except Exception as e:
            logger.warning(f"Reports KPI error: {e}")
            return empty


def _register_breakdown_pie(app: object) -> None:
    """Pie chart: Energy vs Human Capital vs Window Penalties."""

    @app.callback(
        Output("reports-chart-breakdown", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    def update_breakdown_pie(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            hours = _PERIOD_HOURS.get(period, 24.0)
            zones = get_monitored_zones()
            if not zones:
                return empty_chart("No monitored zones available")

            total_energy = 0.0
            total_human = 0.0
            total_window = 0.0

            for zone in zones:
                bleed = compute_financial_bleed(zone.id)
                total_energy += bleed.energy_cost_eur_hr * hours
                total_human += bleed.human_capital_loss_eur_hr * hours
                total_window += bleed.open_window_penalty_eur_hr * hours

            labels = ["Energy Cost", "Human Capital Loss", "Window Penalties"]
            values = [total_energy, total_human, total_window]

            if sum(values) == 0:
                return empty_chart("No financial bleed data for this period")

            fig = go.Figure(
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=[ACCENT_BLUE, STATUS_WARNING, STATUS_CRITICAL]),
                    hole=0.45,
                    textinfo="label+percent",
                    textfont=dict(size=12),
                    hovertemplate="%{label}<br>€%{value:.2f}<br>%{percent}<extra></extra>",
                )
            )

            return apply_chart_theme(fig, "Cost Breakdown by Category")

        except Exception as e:
            logger.warning(f"Reports breakdown pie error: {e}")
            return empty_chart("Error loading chart")


def _register_trend_line(app: object) -> None:
    """Daily cost trend line chart from energy data."""

    @app.callback(
        Output("reports-chart-trend", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    def update_trend_line(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            mapped = TIME_RANGE_MAP.get(period, "today")
            start, end = get_period_range(mapped)
            energy_df = store.get_time_range("energy", start, end)

            if energy_df is None or energy_df.empty:
                return empty_chart("No energy data for this period")

            cfg = DEFAULT_AFI_CONFIG

            # Group by day and compute daily cost
            energy_df = energy_df.copy()
            energy_df["date"] = energy_df["timestamp"].dt.date
            daily = energy_df.groupby("date")["total_kwh"].sum().reset_index()
            daily["cost_eur"] = daily["total_kwh"] * cfg.cost_per_kwh

            if daily.empty:
                return empty_chart("No daily cost data available")

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily["cost_eur"],
                    mode="lines+markers",
                    name="Daily Cost",
                    line=dict(color=ACCENT_BLUE, width=2),
                    marker=dict(size=6),
                    hovertemplate="€%{y:.2f}<br>%{x}<extra></extra>",
                )
            )

            # Add average reference line
            avg_cost = daily["cost_eur"].mean()
            if avg_cost > 0:
                fig.add_hline(
                    y=avg_cost,
                    line_dash="dash",
                    line_color=STATUS_WARNING,
                    annotation_text=f"Avg: €{avg_cost:.2f}",
                    annotation_position="top right",
                )

            fig.update_yaxes(title_text="Cost (€)")
            return apply_chart_theme(fig, "Daily Cost Trend (€)")

        except Exception as e:
            logger.warning(f"Reports trend line error: {e}")
            return empty_chart("Error loading chart")


def _register_zone_ranking(app: object) -> None:
    """Horizontal bar chart of top 10 zones by total financial bleed."""

    @app.callback(
        Output("reports-chart-zones", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    def update_zone_ranking(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            hours = _PERIOD_HOURS.get(period, 24.0)
            zones = get_monitored_zones()
            if not zones:
                return empty_chart("No monitored zones available")

            zone_costs: list[dict[str, object]] = []
            for zone in zones:
                bleed = compute_financial_bleed(zone.id)
                total = bleed.total_bleed_eur_hr * hours
                zone_obj = get_zone_by_id(zone.id)
                name = zone_obj.name if zone_obj else zone.id
                zone_costs.append({"name": name, "cost": total})

            # Sort descending and take top 10
            zone_costs.sort(key=lambda x: x["cost"], reverse=True)
            top_10 = zone_costs[:10]

            if not top_10 or all(z["cost"] == 0 for z in top_10):
                return empty_chart("No zone cost data available")

            names = [z["name"] for z in reversed(top_10)]
            costs = [z["cost"] for z in reversed(top_10)]

            fig = go.Figure(
                go.Bar(
                    x=costs,
                    y=names,
                    orientation="h",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="%{y}<br>€%{x:.2f}<extra></extra>",
                )
            )

            fig.update_xaxes(title_text="Total Cost (€)")
            return apply_chart_theme(fig, "Cost by Zone (Top 10)", height=420)

        except Exception as e:
            logger.warning(f"Reports zone ranking error: {e}")
            return empty_chart("Error loading chart")


def _register_savings_chart(app: object) -> None:
    """Bar chart comparing actual costs vs. baseline costs."""

    @app.callback(
        Output("reports-chart-savings", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    def update_savings_chart(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            mapped = TIME_RANGE_MAP.get(period, "today")
            start, end = get_period_range(mapped)
            energy_df = store.get_time_range("energy", start, end)

            if energy_df is None or energy_df.empty:
                return empty_chart("No energy data for savings comparison")

            cfg = DEFAULT_AFI_CONFIG
            energy_df = energy_df.copy()
            energy_df["date"] = energy_df["timestamp"].dt.date

            daily = energy_df.groupby("date")["total_kwh"].sum().reset_index()
            daily["actual_cost"] = daily["total_kwh"] * cfg.cost_per_kwh

            # Compute baseline as rolling mean + 10% overhead
            overall_mean = daily["actual_cost"].mean()
            daily["baseline_cost"] = overall_mean * 1.10

            if daily.empty:
                return empty_chart("No savings data available")

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=daily["date"],
                    y=daily["baseline_cost"],
                    name="Baseline",
                    marker=dict(color=STATUS_WARNING, opacity=0.5),
                    hovertemplate="Baseline: €%{y:.2f}<extra></extra>",
                )
            )

            fig.add_trace(
                go.Bar(
                    x=daily["date"],
                    y=daily["actual_cost"],
                    name="Actual",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="Actual: €%{y:.2f}<extra></extra>",
                )
            )

            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="Cost (€)")
            return apply_chart_theme(fig, "Savings vs. Baseline")

        except Exception as e:
            logger.warning(f"Reports savings chart error: {e}")
            return empty_chart("Error loading chart")
