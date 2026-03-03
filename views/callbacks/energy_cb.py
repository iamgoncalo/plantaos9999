"""Energy page callbacks.

Registers callbacks for KPIs and four charts on the energy detail page.
Data flows from the DataStore through time-range filtering to Plotly figures.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, no_update
from loguru import logger

from config.building import get_monitored_zones, get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    CHART_COLORS,
    STATUS_CRITICAL,
    TEXT_TERTIARY,
)
from core.baseline import compute_time_of_day_baseline
from data.store import store
from utils.formatters import format_energy
from utils.time_utils import get_period_range
from views.charts import (
    HEATMAP_COLORSCALE,
    TIME_RANGE_MAP,
    apply_chart_theme,
    empty_chart,
)
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback


def register_energy_callbacks(app: object) -> None:
    """Register all energy page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_energy_kpis(app)
    _register_energy_timeline(app)
    _register_energy_breakdown(app)
    _register_energy_heatmap(app)
    _register_energy_scatter(app)


def _get_energy_data(time_range: str) -> pd.DataFrame | None:
    """Fetch energy data for the selected time range with NaN guard."""
    period = TIME_RANGE_MAP.get(time_range, "today")
    start, end = get_period_range(period)
    df = store.get_time_range("energy", start, end)
    if df is None or df.empty:
        return None
    energy_cols = [
        "total_kwh",
        "hvac_kwh",
        "lighting_kwh",
        "equipment_kwh",
        "other_kwh",
    ]
    for col in energy_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill().fillna(0)
    return df


def _register_energy_kpis(app: object) -> None:
    """Update energy KPI cards."""

    @app.callback(
        Output("energy-kpi-grid", "children"),
        Input("energy-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_energy_kpis(time_range: str, _n: int, pathname: str | None) -> list:
        if pathname != "/energy":
            return no_update

        _empty = [
            create_kpi_card("Total Consumption", "—", icon="mdi:flash"),
            create_kpi_card("vs. Baseline", "—", icon="mdi:chart-line"),
            create_kpi_card("Peak Hour", "—", icon="mdi:clock-alert-outline"),
            create_kpi_card("Cost Estimate", "—", icon="mdi:currency-eur"),
        ]

        try:
            df = _get_energy_data(time_range)
        except Exception as e:
            logger.warning(f"Energy KPI data fetch error: {e}")
            return _empty

        if df is None or df.empty:
            return _empty

        try:
            return _compute_energy_kpis(df)
        except Exception as e:
            logger.warning(f"Energy KPIs compute error: {e}")
            return _empty

    def _compute_energy_kpis(df: pd.DataFrame) -> list:
        total_kwh = df["total_kwh"].sum()

        # vs Baseline: compare daily average to 7-day baseline
        n_days = max(1, (df["timestamp"].max() - df["timestamp"].min()).days or 1)
        daily_avg = total_kwh / n_days

        # Get building-wide baseline from all zones
        baseline_df = store.get("energy")
        if baseline_df is not None and not baseline_df.empty:
            hourly_total = baseline_df.groupby(pd.Grouper(key="timestamp", freq="1D"))[
                "total_kwh"
            ].sum()
            baseline_mean = hourly_total.mean() if not hourly_total.empty else 0
            if baseline_mean > 0:
                pct_diff = ((daily_avg - baseline_mean) / baseline_mean) * 100
                baseline_str = f"{pct_diff:+.1f}"
                baseline_trend = pct_diff
            else:
                baseline_str = "—"
                baseline_trend = None
        else:
            baseline_str = "—"
            baseline_trend = None

        # Peak hour
        if "timestamp" in df.columns:
            hourly = df.groupby(df["timestamp"].dt.hour)["total_kwh"].sum()
            if not hourly.empty:
                peak_h = int(hourly.idxmax())
                peak_str = f"{peak_h:02d}:00"
            else:
                peak_str = "—"
        else:
            peak_str = "—"

        # Cost at €0.15/kWh
        cost = total_kwh * 0.15
        cost_str = f"{cost:.0f}" if cost >= 1 else f"{cost:.2f}"

        return [
            create_kpi_card(
                "Total Consumption",
                format_energy(total_kwh),
                icon="mdi:flash",
            ),
            create_kpi_card(
                "vs. Baseline",
                baseline_str,
                unit="%",
                trend=baseline_trend,
                icon="mdi:chart-line",
            ),
            create_kpi_card(
                "Peak Hour",
                peak_str,
                icon="mdi:clock-alert-outline",
            ),
            create_kpi_card(
                "Cost Estimate",
                cost_str,
                unit="€",
                icon="mdi:currency-eur",
            ),
        ]


def _register_energy_timeline(app: object) -> None:
    """24h energy timeline with baseline band and anomaly markers."""

    @app.callback(
        Output("energy-chart-timeline", "figure"),
        Input("energy-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_energy_timeline(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/energy":
            return no_update
        try:
            return _energy_timeline_impl(time_range)
        except Exception as e:
            logger.warning(f"Energy timeline error: {e}")
            return empty_chart("Error loading chart")

    def _energy_timeline_impl(time_range: str) -> go.Figure:
        df = _get_energy_data(time_range)
        if df is None or df.empty:
            return empty_chart("No energy data available")

        # Aggregate all zones by hour
        hourly = (
            df.groupby(pd.Grouper(key="timestamp", freq="1h"))["total_kwh"]
            .sum()
            .reset_index()
        )
        hourly = hourly.dropna(subset=["total_kwh"])

        if hourly.empty:
            return empty_chart("No energy data for this period")

        # Compute baseline band from time-of-day baseline
        full_energy = store.get("energy")
        if full_energy is not None and not full_energy.empty:
            tod_baseline = compute_time_of_day_baseline(full_energy, "total_kwh")
            if not tod_baseline.empty:
                # Map baseline mean/std to hourly timestamps
                hourly["hour"] = hourly["timestamp"].dt.hour
                hourly["dow"] = hourly["timestamp"].dt.dayofweek
                hourly = hourly.merge(
                    tod_baseline,
                    on=["hour", "day_of_week"]
                    if "day_of_week" in tod_baseline.columns
                    else ["hour"],
                    how="left",
                    suffixes=("", "_bl"),
                )
                # Scale baseline by number of zones
                n_zones = df["zone_id"].nunique()
                hourly["bl_mean"] = hourly.get("mean", 0) * n_zones
                hourly["bl_std"] = hourly.get("std", 0) * n_zones
                hourly["upper"] = hourly["bl_mean"] + hourly["bl_std"]
                hourly["lower"] = (hourly["bl_mean"] - hourly["bl_std"]).clip(lower=0)
                has_baseline = True
            else:
                has_baseline = False
        else:
            has_baseline = False

        fig = go.Figure()

        # Baseline band
        if has_baseline and "upper" in hourly.columns:
            fig.add_trace(
                go.Scatter(
                    x=hourly["timestamp"],
                    y=hourly["upper"],
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=hourly["timestamp"],
                    y=hourly["lower"],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(0, 113, 227, 0.08)",
                    name="Baseline ±1σ",
                    hoverinfo="skip",
                )
            )

        # Actual line
        fig.add_trace(
            go.Scatter(
                x=hourly["timestamp"],
                y=hourly["total_kwh"],
                mode="lines",
                name="Actual",
                line=dict(color=ACCENT_BLUE, width=2),
            )
        )

        # Anomaly markers: points > 2σ from baseline
        if has_baseline and "bl_mean" in hourly.columns:
            anomalies = hourly[
                (hourly["bl_std"] > 0)
                & (abs(hourly["total_kwh"] - hourly["bl_mean"]) > 2 * hourly["bl_std"])
            ]
            if not anomalies.empty:
                fig.add_trace(
                    go.Scatter(
                        x=anomalies["timestamp"],
                        y=anomalies["total_kwh"],
                        mode="markers",
                        name="Anomaly",
                        marker=dict(color=STATUS_CRITICAL, size=9, symbol="circle"),
                    )
                )

        fig.update_yaxes(title_text="Energy (kWh)")
        return apply_chart_theme(fig, "Energy vs. Baseline")


def _register_energy_breakdown(app: object) -> None:
    """Stacked area chart of energy by category."""

    @app.callback(
        Output("energy-chart-breakdown", "figure"),
        Input("energy-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_energy_breakdown(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/energy":
            return no_update
        try:
            df = _get_energy_data(time_range)
            if df is None or df.empty:
                return empty_chart("No energy data available")

            categories = ["hvac_kwh", "lighting_kwh", "equipment_kwh", "other_kwh"]
            labels = ["HVAC", "Lighting", "Equipment", "Other"]
            colors = CHART_COLORS[:4]

            # Aggregate by hour
            hourly = (
                df.groupby(pd.Grouper(key="timestamp", freq="1h"))[categories]
                .sum()
                .reset_index()
            )
            hourly = hourly.dropna()

            if hourly.empty:
                return empty_chart("No energy breakdown data")

            fig = go.Figure()
            for col, label, color in zip(categories, labels, colors):
                fig.add_trace(
                    go.Scatter(
                        x=hourly["timestamp"],
                        y=hourly[col],
                        name=label,
                        stackgroup="one",
                        line=dict(width=0.5, color=color),
                    )
                )

            fig.update_yaxes(title_text="Energy (kWh)")
            return apply_chart_theme(fig, "Consumption by Category")
        except Exception as e:
            logger.warning(f"Energy breakdown chart error: {e}")
            return empty_chart("Error loading chart")


def _register_energy_heatmap(app: object) -> None:
    """Zone × hour energy heatmap."""

    @app.callback(
        Output("energy-chart-heatmap", "figure"),
        Input("energy-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_energy_heatmap(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/energy":
            return no_update
        try:
            df = _get_energy_data(time_range)
            if df is None or df.empty:
                return empty_chart("No energy data available")

            df = df.copy()
            df["hour"] = df["timestamp"].dt.hour

            # Only monitored zones
            monitored_ids = {z.id for z in get_monitored_zones()}
            df = df[df["zone_id"].isin(monitored_ids)]

            if df.empty:
                return empty_chart("No zone energy data")

            pivot = df.pivot_table(
                values="total_kwh",
                index="zone_id",
                columns="hour",
                aggfunc="mean",
            ).fillna(0)

            # Replace zone_ids with short names
            zone_names = []
            for zid in pivot.index:
                z = get_zone_by_id(zid)
                zone_names.append(z.name if z else zid)

            fig = go.Figure(
                go.Heatmap(
                    z=pivot.values,
                    x=[f"{h:02d}:00" for h in pivot.columns],
                    y=zone_names,
                    colorscale=HEATMAP_COLORSCALE,
                    colorbar=dict(title="kWh"),
                    hovertemplate=("%{y}<br>%{x}<br>%{z:.2f} kWh<extra></extra>"),
                )
            )

            return apply_chart_theme(fig, "Zone Energy Heatmap", height=420)
        except Exception as e:
            logger.warning(f"Energy heatmap error: {e}")
            return empty_chart("Error loading chart")


def _register_energy_scatter(app: object) -> None:
    """Energy vs occupancy scatter plot."""

    @app.callback(
        Output("energy-chart-scatter", "figure"),
        Input("energy-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_energy_scatter(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/energy":
            return no_update
        try:
            period = TIME_RANGE_MAP.get(time_range, "today")
            start, end = get_period_range(period)

            energy_df = store.get_time_range("energy", start, end)
            occ_df = store.get_time_range("occupancy", start, end)

            if energy_df is None or occ_df is None or energy_df.empty or occ_df.empty:
                return empty_chart("No data for energy-occupancy correlation")

            # Aggregate occupancy to 15-min to match energy resolution
            occ_agg = (
                occ_df.groupby([pd.Grouper(key="timestamp", freq="15min"), "zone_id"])[
                    "occupant_count"
                ]
                .mean()
                .reset_index()
            )

            # Merge
            merged = energy_df.merge(occ_agg, on=["timestamp", "zone_id"], how="inner")

            if merged.empty:
                return empty_chart("No overlapping energy-occupancy data")

            # Assign color index per zone
            zone_ids = merged["zone_id"].unique()
            zone_color_map = {
                zid: CHART_COLORS[i % len(CHART_COLORS)]
                for i, zid in enumerate(zone_ids)
            }
            merged["color"] = merged["zone_id"].map(zone_color_map)

            fig = go.Figure()

            # Scatter points
            for zid in zone_ids[:8]:
                z = get_zone_by_id(zid)
                name = z.name if z else zid
                zdf = merged[merged["zone_id"] == zid]
                fig.add_trace(
                    go.Scatter(
                        x=zdf["occupant_count"],
                        y=zdf["total_kwh"],
                        mode="markers",
                        name=name,
                        marker=dict(
                            size=5,
                            opacity=0.5,
                            color=zone_color_map[zid],
                        ),
                        hovertemplate=(
                            f"{name}<br>"
                            "Occupancy: %{x:.0f}<br>"
                            "Energy: %{y:.2f} kWh<extra></extra>"
                        ),
                    )
                )

            # OLS trendline across all points
            x_all = merged["occupant_count"].values
            y_all = merged["total_kwh"].values
            valid = ~(np.isnan(x_all) | np.isnan(y_all))
            if valid.sum() > 2:
                coeffs = np.polyfit(x_all[valid], y_all[valid], 1)
                x_line = np.linspace(x_all[valid].min(), x_all[valid].max(), 50)
                y_line = np.polyval(coeffs, x_line)
                fig.add_trace(
                    go.Scatter(
                        x=x_line,
                        y=y_line,
                        mode="lines",
                        name="Trend",
                        line=dict(color=TEXT_TERTIARY, width=1.5, dash="dash"),
                        showlegend=False,
                    )
                )

            fig.update_xaxes(title_text="Occupancy (people)")
            fig.update_yaxes(title_text="Energy (kWh)")
            return apply_chart_theme(fig, "Energy vs. Occupancy")
        except Exception as e:
            logger.warning(f"Energy scatter chart error: {e}")
            return empty_chart("Error loading chart")
