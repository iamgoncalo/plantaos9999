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
from views.components.safe_callback import safe_callback


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
    _register_pdf_download(app)


def _register_reports_kpis(app: object) -> None:
    """Update financial KPI cards from AFI engine bleed data."""

    @app.callback(
        Output("reports-kpi-grid", "children"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_reports_kpis(_n: int, period: str, pathname: str | None) -> list:
        if pathname != "/reports":
            return no_update

        empty = [
            create_kpi_card("Total Energy Cost", "—", unit="€", icon="mdi:flash"),
            create_kpi_card(
                "Productivity Impact", "—", unit="€", icon="mdi:account-group"
            ),
            create_kpi_card(
                "HVAC Waste", "—", unit="€", icon="mdi:window-open-variant"
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
                    "Productivity Impact",
                    f"{total_human:.0f}" if total_human >= 1 else f"{total_human:.2f}",
                    unit="€",
                    icon="mdi:account-group",
                ),
                create_kpi_card(
                    "HVAC Waste",
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
    """Pie chart: Energy vs Productivity Impact vs HVAC Waste."""

    @app.callback(
        Output("reports-chart-breakdown", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    @safe_callback
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

            labels = ["Energy Cost", "Productivity Impact", "HVAC Waste"]
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
            return empty_chart("Aguardando dados...")


def _register_trend_line(app: object) -> None:
    """Daily cost trend line chart from energy data."""

    @app.callback(
        Output("reports-chart-trend", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_trend_line(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            mapped = TIME_RANGE_MAP.get(period, "today")
            start, end = get_period_range(mapped)
            energy_df = store.get_time_range("energy", start, end)

            if energy_df is None or energy_df.empty:
                return empty_chart(
                    "No energy data for this period. Visit Settings to generate demo data."
                )

            # Column existence checks
            if "timestamp" not in energy_df.columns:
                return empty_chart("Missing timestamp column")
            if "total_kwh" not in energy_df.columns:
                return empty_chart("Missing total_kwh column")

            cfg = DEFAULT_AFI_CONFIG

            # NaN guard
            energy_df = energy_df.copy()
            for col in energy_df.select_dtypes(include=["number"]).columns:
                energy_df[col] = energy_df[col].ffill().bfill().fillna(0)

            # Group by hour (today) or day (7d/30d)
            if period == "today":
                energy_df["x_col"] = energy_df["timestamp"].dt.floor("h")
                grouped = energy_df.groupby("x_col")["total_kwh"].sum().reset_index()
                grouped["cost_eur"] = grouped["total_kwh"] * cfg.cost_per_kwh
                chart_title = "Hourly Cost Trend (\u20ac)"
                trace_name = "Hourly Cost"
            else:
                energy_df["x_col"] = energy_df["timestamp"].dt.date
                grouped = energy_df.groupby("x_col")["total_kwh"].sum().reset_index()
                grouped["cost_eur"] = grouped["total_kwh"] * cfg.cost_per_kwh
                chart_title = "Daily Cost Trend (\u20ac)"
                trace_name = "Daily Cost"

            if grouped.empty:
                return empty_chart(
                    "No energy data for the selected period. Try a longer time range."
                )

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=grouped["x_col"],
                    y=grouped["cost_eur"],
                    mode="lines+markers",
                    name=trace_name,
                    line=dict(color=ACCENT_BLUE, width=2),
                    marker=dict(size=6),
                    hovertemplate="\u20ac%{y:.2f}<br>%{x}<extra></extra>",
                )
            )

            # Add average reference line
            avg_cost = grouped["cost_eur"].mean()
            if avg_cost > 0:
                fig.add_hline(
                    y=avg_cost,
                    line_dash="dash",
                    line_color=STATUS_WARNING,
                    annotation_text=f"Avg: \u20ac{avg_cost:.2f}",
                    annotation_position="top right",
                )

            fig.update_yaxes(title_text="Cost (\u20ac)")
            return apply_chart_theme(fig, chart_title)

        except Exception as e:
            logger.error(f"Reports trend line error: {e}")
            return empty_chart(
                "Unable to load cost trend. Visit Settings to generate demo data."
            )


def _register_zone_ranking(app: object) -> None:
    """Horizontal bar chart of top 10 zones by total financial bleed."""

    @app.callback(
        Output("reports-chart-zones", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    @safe_callback
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
                try:
                    bleed = compute_financial_bleed(zone.id)
                    total = bleed.total_bleed_eur_hr * hours
                except Exception:
                    total = 0.0
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
                    hovertemplate="%{y}<br>\u20ac%{x:.2f}<extra></extra>",
                )
            )

            fig.update_xaxes(title_text="Total Cost (\u20ac)")
            return apply_chart_theme(fig, "Cost by Zone (Top 10)", height=420)

        except Exception as e:
            logger.warning(f"Reports zone ranking error: {e}")
            return empty_chart("Aguardando dados...")


def _register_savings_chart(app: object) -> None:
    """Bar chart comparing actual costs vs. baseline costs."""

    @app.callback(
        Output("reports-chart-savings", "figure"),
        Input("data-refresh-interval", "n_intervals"),
        Input("reports-period", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_savings_chart(_n: int, period: str, pathname: str | None) -> go.Figure:
        if pathname != "/reports":
            return no_update
        try:
            mapped = TIME_RANGE_MAP.get(period, "today")
            start, end = get_period_range(mapped)
            energy_df = store.get_time_range("energy", start, end)

            if energy_df is None or energy_df.empty:
                return empty_chart(
                    "No energy data for this period. Visit Settings to generate demo data."
                )

            # Column existence checks
            if "timestamp" not in energy_df.columns:
                return empty_chart("Missing timestamp column")
            if "total_kwh" not in energy_df.columns:
                return empty_chart("Missing total_kwh column")

            cfg = DEFAULT_AFI_CONFIG
            energy_df = energy_df.copy()
            for col in energy_df.select_dtypes(include=["number"]).columns:
                energy_df[col] = energy_df[col].ffill().bfill().fillna(0)

            # Group by hour (today) or day (7d/30d)
            if period == "today":
                energy_df["x_col"] = energy_df["timestamp"].dt.floor("h")
            else:
                energy_df["x_col"] = energy_df["timestamp"].dt.date

            grouped = energy_df.groupby("x_col")["total_kwh"].sum().reset_index()
            grouped["actual_cost"] = grouped["total_kwh"] * cfg.cost_per_kwh

            # Compute baseline as rolling mean + 10% overhead
            overall_mean = grouped["actual_cost"].mean()
            grouped["baseline_cost"] = overall_mean * 1.10

            if grouped.empty:
                return empty_chart(
                    "No energy data for the selected period. Try a longer time range."
                )

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=grouped["x_col"],
                    y=grouped["baseline_cost"],
                    name="Baseline",
                    marker=dict(color=STATUS_WARNING, opacity=0.5),
                    hovertemplate="Baseline: \u20ac%{y:.2f}<extra></extra>",
                )
            )

            fig.add_trace(
                go.Bar(
                    x=grouped["x_col"],
                    y=grouped["actual_cost"],
                    name="Actual",
                    marker=dict(color=ACCENT_BLUE),
                    hovertemplate="Actual: \u20ac%{y:.2f}<extra></extra>",
                )
            )

            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="Cost (\u20ac)")
            return apply_chart_theme(fig, "Savings vs. Baseline")

        except Exception as e:
            logger.error(f"Reports savings chart error: {e}")
            return empty_chart(
                "Unable to load savings chart. Visit Settings to generate demo data."
            )


def _register_pdf_download(app: object) -> None:
    """Download report with confirmation dialog."""

    @app.callback(
        Output("reports-confirm-download", "displayed"),
        Input("reports-download-pdf-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_download_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before downloading report."""
        return bool(n_clicks)

    @app.callback(
        Output("reports-pdf-download", "data"),
        Input("reports-confirm-download", "submit_n_clicks"),
        State("reports-period", "value"),
        State("tenant-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def download_report(
        n_clicks: int | None,
        period: str,
        tenant: str | None,
        pathname: str | None,
    ) -> dict | None:
        """Download PDF report with tenant and date in filename.

        Args:
            n_clicks: Confirm dialog submit click count.
            period: Report period ('today', '7d', '30d').
            tenant: Active tenant identifier.
            pathname: Current URL path.

        Returns:
            Download dict for dcc.Download or no_update.
        """
        if pathname != "/reports" or not n_clicks:
            return no_update

        import base64
        from datetime import datetime

        tenant_slug = tenant or "horse_renault"
        date_str = datetime.now().strftime("%Y%m%d")

        # Try real PDF first
        try:
            from utils.pdf_report import generate_report_pdf

            pdf_bytes = generate_report_pdf(period=period)
            filename = f"plantaos_report_{tenant_slug}_{date_str}.pdf"
            return dict(
                content=base64.b64encode(pdf_bytes).decode(),
                filename=filename,
                type="application/pdf",
                base64=True,
            )
        except Exception as e:
            logger.warning(f"PDF generation error, falling back to HTML: {e}")

        # Fallback to HTML
        try:
            from utils.pdf_report import generate_report_html

            html_content = generate_report_html(period=period)
            filename = f"plantaos_report_{tenant_slug}_{date_str}.html"
            return dict(content=html_content, filename=filename, type="text/html")
        except Exception as e:
            logger.warning(f"HTML report error: {e}")

        # Last resort: CSV
        try:
            from utils.pdf_report import generate_report_csv

            csv_content = generate_report_csv(period=period)
            filename = f"plantaos_report_{tenant_slug}_{date_str}.csv"
            return dict(
                content=csv_content,
                filename=filename,
                type="text/csv",
            )
        except Exception as e2:
            logger.warning(f"CSV fallback error: {e2}")
            return no_update
