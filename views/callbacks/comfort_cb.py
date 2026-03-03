"""Comfort page callbacks.

Registers callbacks for KPIs and four charts on the comfort detail page.
Data flows from the DataStore with optional zone filtering.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output

from config.building import get_monitored_zones, get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    CHART_COLORS,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
)
from config.thresholds import COMFORT_BANDS
from data.store import store
from utils.time_utils import get_period_range
from views.charts import (
    COMFORT_COLORSCALE,
    apply_chart_theme,
    empty_chart,
)
from views.components.kpi_card import create_kpi_card


def register_comfort_callbacks(app: object) -> None:
    """Register all comfort page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_comfort_kpis(app)
    _register_comfort_temperature(app)
    _register_comfort_matrix(app)
    _register_comfort_co2_scatter(app)
    _register_comfort_humidity(app)


def _get_comfort_data(
    zones: list[str] | None = None,
) -> pd.DataFrame | None:
    """Fetch last 24h of comfort data, optionally filtered by zones."""
    start, end = get_period_range("today")
    df = store.get_time_range("comfort", start, end)
    if df is None or df.empty:
        # Fallback: try last 7 days
        start, end = get_period_range("last_7d")
        df = store.get_time_range("comfort", start, end)
    if df is None or df.empty:
        return None
    if zones:
        df = df[df["zone_id"].isin(zones)]
    return df


def _monitored_zone_ids() -> list[str]:
    """Get IDs of all monitored zones."""
    return [z.id for z in get_monitored_zones()]


def _register_comfort_kpis(app: object) -> None:
    """Update comfort KPI cards."""

    @app.callback(
        Output("comfort-kpi-grid", "children"),
        Input("comfort-zone-filter", "value"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_comfort_kpis(zones: list[str] | None, _n: int) -> list:
        df = _get_comfort_data(zones)

        if df is None or df.empty:
            return [
                create_kpi_card("Avg Temperature", "—", icon="mdi:thermometer"),
                create_kpi_card("Avg Humidity", "—", icon="mdi:water-percent"),
                create_kpi_card("Avg CO₂", "—", icon="mdi:molecule-co2"),
                create_kpi_card(
                    "In Comfort Band", "—", icon="mdi:check-circle-outline"
                ),
            ]

        avg_temp = df["temperature_c"].mean()
        avg_hum = df["humidity_pct"].mean()
        avg_co2 = df["co2_ppm"].mean()

        # Compute % time in comfort band (all 4 metrics in optimal range)
        temp_band = COMFORT_BANDS["temperature"]
        hum_band = COMFORT_BANDS["humidity"]
        co2_band = COMFORT_BANDS["co2"]

        in_band = (
            (df["temperature_c"] >= temp_band.min_optimal)
            & (df["temperature_c"] <= temp_band.max_optimal)
            & (df["humidity_pct"] >= hum_band.min_optimal)
            & (df["humidity_pct"] <= hum_band.max_optimal)
            & (df["co2_ppm"] >= co2_band.min_optimal)
            & (df["co2_ppm"] <= co2_band.max_optimal)
        )
        pct_in_band = (in_band.sum() / len(in_band)) * 100 if len(df) > 0 else 0

        return [
            create_kpi_card(
                "Avg Temperature",
                f"{avg_temp:.1f}",
                unit="°C",
                icon="mdi:thermometer",
            ),
            create_kpi_card(
                "Avg Humidity",
                f"{avg_hum:.0f}",
                unit="%",
                icon="mdi:water-percent",
            ),
            create_kpi_card(
                "Avg CO₂",
                f"{avg_co2:.0f}",
                unit="ppm",
                icon="mdi:molecule-co2",
            ),
            create_kpi_card(
                "In Comfort Band",
                f"{pct_in_band:.0f}",
                unit="%",
                icon="mdi:check-circle-outline",
            ),
        ]


def _register_comfort_temperature(app: object) -> None:
    """Temperature timeline per zone with comfort band."""

    @app.callback(
        Output("comfort-chart-temperature", "figure"),
        Input("comfort-zone-filter", "value"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_comfort_temperature(zones: list[str] | None, _n: int) -> go.Figure:
        df = _get_comfort_data(zones)
        if df is None or df.empty:
            return empty_chart("No comfort data available")

        # Use selected zones or top 8 monitored zones
        if zones:
            zone_ids = zones[:8]
        else:
            zone_ids = _monitored_zone_ids()[:8]

        fig = go.Figure()

        # Comfort band shading
        temp_band = COMFORT_BANDS["temperature"]
        fig.add_hrect(
            y0=temp_band.min_optimal,
            y1=temp_band.max_optimal,
            fillcolor="rgba(52, 199, 89, 0.08)",
            line_width=0,
            annotation_text="Optimal",
            annotation_position="top left",
            annotation_font_color=STATUS_HEALTHY,
            annotation_font_size=10,
        )

        # One line per zone
        for i, zid in enumerate(zone_ids):
            zdf = df[df["zone_id"] == zid].sort_values("timestamp")
            if zdf.empty:
                continue
            z = get_zone_by_id(zid)
            name = z.name if z else zid
            color = CHART_COLORS[i % len(CHART_COLORS)]

            # Downsample for performance: take hourly mean
            zdf_hourly = (
                zdf.set_index("timestamp")
                .resample("15min")["temperature_c"]
                .mean()
                .dropna()
                .reset_index()
            )

            fig.add_trace(
                go.Scatter(
                    x=zdf_hourly["timestamp"],
                    y=zdf_hourly["temperature_c"],
                    mode="lines",
                    name=name,
                    line=dict(width=1.5, color=color),
                )
            )

        fig.update_yaxes(title_text="Temperature (°C)")
        return apply_chart_theme(fig, "Temperature by Zone")


def _register_comfort_matrix(app: object) -> None:
    """Comfort compliance matrix heatmap (zones × metrics)."""

    @app.callback(
        Output("comfort-chart-matrix", "figure"),
        Input("comfort-zone-filter", "value"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_comfort_matrix(zones: list[str] | None, _n: int) -> go.Figure:
        df = _get_comfort_data(zones)
        if df is None or df.empty:
            return empty_chart("No comfort data available")

        zone_ids = zones if zones else _monitored_zone_ids()

        metrics = [
            ("temperature_c", "Temperature", "temperature"),
            ("humidity_pct", "Humidity", "humidity"),
            ("co2_ppm", "CO₂", "co2"),
            ("illuminance_lux", "Illuminance", "illuminance"),
        ]

        z_values = []
        zone_names = []
        text_values = []

        for zid in zone_ids:
            zdf = df[df["zone_id"] == zid]
            if zdf.empty:
                continue
            z = get_zone_by_id(zid)
            zone_names.append(z.name if z else zid)

            row = []
            text_row = []
            for col, label, band_key in metrics:
                if col not in zdf.columns or zdf[col].isna().all():
                    row.append(0)
                    text_row.append("—")
                    continue
                band = COMFORT_BANDS.get(band_key)
                if band is None:
                    row.append(50)
                    text_row.append("N/A")
                    continue
                in_optimal = (zdf[col] >= band.min_optimal) & (
                    zdf[col] <= band.max_optimal
                )
                pct = (in_optimal.sum() / len(zdf)) * 100
                row.append(round(pct, 1))
                text_row.append(f"{pct:.0f}%")

            z_values.append(row)
            text_values.append(text_row)

        if not z_values:
            return empty_chart("No zone data for comfort matrix")

        metric_labels = [m[1] for m in metrics]

        fig = go.Figure(
            go.Heatmap(
                z=z_values,
                x=metric_labels,
                y=zone_names,
                colorscale=COMFORT_COLORSCALE,
                zmin=0,
                zmax=100,
                text=text_values,
                texttemplate="%{text}",
                textfont=dict(size=11),
                colorbar=dict(title="% In Band"),
                hovertemplate=("%{y}<br>%{x}: %{z:.1f}%<extra></extra>"),
            )
        )

        return apply_chart_theme(fig, "Comfort Compliance Matrix", height=420)


def _register_comfort_co2_scatter(app: object) -> None:
    """CO₂ vs occupancy scatter with trendline."""

    @app.callback(
        Output("comfort-chart-co2", "figure"),
        Input("comfort-zone-filter", "value"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_co2_scatter(zones: list[str] | None, _n: int) -> go.Figure:
        comfort_df = _get_comfort_data(zones)
        if comfort_df is None or comfort_df.empty:
            return empty_chart("No comfort data available")

        # Get occupancy for the same period
        start, end = get_period_range("today")
        occ_df = store.get_time_range("occupancy", start, end)
        if occ_df is None or occ_df.empty:
            start, end = get_period_range("last_7d")
            occ_df = store.get_time_range("occupancy", start, end)

        if occ_df is None or occ_df.empty:
            return empty_chart("No occupancy data for correlation")

        if zones:
            occ_df = occ_df[occ_df["zone_id"].isin(zones)]

        # Align: aggregate both to 15-min per zone
        comfort_agg = (
            comfort_df.groupby([pd.Grouper(key="timestamp", freq="15min"), "zone_id"])[
                "co2_ppm"
            ]
            .mean()
            .reset_index()
        )
        occ_agg = (
            occ_df.groupby([pd.Grouper(key="timestamp", freq="15min"), "zone_id"])[
                "occupant_count"
            ]
            .mean()
            .reset_index()
        )

        merged = comfort_agg.merge(occ_agg, on=["timestamp", "zone_id"], how="inner")

        if merged.empty:
            return empty_chart("No overlapping CO₂-occupancy data")

        fig = go.Figure()

        # Scatter
        fig.add_trace(
            go.Scatter(
                x=merged["occupant_count"],
                y=merged["co2_ppm"],
                mode="markers",
                name="CO₂ readings",
                marker=dict(
                    size=4,
                    opacity=0.4,
                    color=ACCENT_BLUE,
                ),
                hovertemplate=(
                    "Occupancy: %{x:.0f}<br>CO₂: %{y:.0f} ppm<extra></extra>"
                ),
            )
        )

        # Trendline
        x = merged["occupant_count"].values
        y = merged["co2_ppm"].values
        valid = ~(np.isnan(x) | np.isnan(y))
        if valid.sum() > 2:
            coeffs = np.polyfit(x[valid], y[valid], 1)
            x_line = np.linspace(x[valid].min(), x[valid].max(), 50)
            y_line = np.polyval(coeffs, x_line)
            fig.add_trace(
                go.Scatter(
                    x=x_line,
                    y=y_line,
                    mode="lines",
                    name="Trend",
                    line=dict(color=STATUS_WARNING, width=2, dash="dash"),
                )
            )

        # Reference lines for CO₂ thresholds
        co2_band = COMFORT_BANDS["co2"]
        fig.add_hline(
            y=co2_band.max_optimal,
            line_dash="dot",
            line_color=STATUS_WARNING,
            annotation_text=f"Optimal max ({co2_band.max_optimal:.0f} ppm)",
            annotation_font_size=10,
        )
        fig.add_hline(
            y=co2_band.max_acceptable,
            line_dash="dot",
            line_color=STATUS_CRITICAL,
            annotation_text=f"Acceptable max ({co2_band.max_acceptable:.0f} ppm)",
            annotation_font_size=10,
        )

        fig.update_xaxes(title_text="Occupancy (people)")
        fig.update_yaxes(title_text="CO₂ (ppm)")
        return apply_chart_theme(fig, "CO₂ vs. Occupancy")


def _register_comfort_humidity(app: object) -> None:
    """Humidity distribution violin plot by zone."""

    @app.callback(
        Output("comfort-chart-humidity", "figure"),
        Input("comfort-zone-filter", "value"),
        Input("data-refresh-interval", "n_intervals"),
    )
    def update_humidity_violin(zones: list[str] | None, _n: int) -> go.Figure:
        df = _get_comfort_data(zones)
        if df is None or df.empty:
            return empty_chart("No comfort data available")

        zone_ids = zones if zones else _monitored_zone_ids()[:10]

        fig = go.Figure()

        for i, zid in enumerate(zone_ids):
            zdf = df[df["zone_id"] == zid]
            if zdf.empty or zdf["humidity_pct"].isna().all():
                continue
            z = get_zone_by_id(zid)
            name = z.name if z else zid
            # Shorten long names
            short = name[:15] + "…" if len(name) > 15 else name
            color = CHART_COLORS[i % len(CHART_COLORS)]

            fig.add_trace(
                go.Violin(
                    y=zdf["humidity_pct"],
                    name=short,
                    box_visible=True,
                    meanline_visible=True,
                    fillcolor=color,
                    opacity=0.6,
                    line_color=color,
                )
            )

        # Comfort band lines
        hum_band = COMFORT_BANDS["humidity"]
        fig.add_hline(
            y=hum_band.min_optimal,
            line_dash="dot",
            line_color=STATUS_WARNING,
            annotation_text="Min optimal",
            annotation_font_size=10,
        )
        fig.add_hline(
            y=hum_band.max_optimal,
            line_dash="dot",
            line_color=STATUS_WARNING,
            annotation_text="Max optimal",
            annotation_font_size=10,
        )

        fig.update_yaxes(title_text="Humidity (%)")
        return apply_chart_theme(fig, "Humidity Distribution")
