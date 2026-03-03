"""Occupancy page callbacks.

Registers callbacks for KPIs and four charts on the occupancy detail page.
Includes timeline, utilization heatmap, Sankey flow, and space efficiency.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, no_update

from config.building import get_monitored_zones, get_zone_by_id
from config.theme import (
    ACCENT_BLUE,
    CHART_COLORS,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_TERTIARY,
)
from core.baseline import compute_time_of_day_baseline
from data.store import store
from utils.time_utils import get_period_range
from views.charts import (
    TIME_RANGE_MAP,
    UTILIZATION_COLORSCALE,
    apply_chart_theme,
    empty_chart,
)
from views.components.kpi_card import create_kpi_card


def register_occupancy_callbacks(app: object) -> None:
    """Register all occupancy page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_occ_kpis(app)
    _register_occ_timeline(app)
    _register_occ_heatmap(app)
    _register_occ_sankey(app)
    _register_occ_efficiency(app)


def _get_occ_data(time_range: str) -> pd.DataFrame | None:
    """Fetch occupancy data for the selected time range."""
    period = TIME_RANGE_MAP.get(time_range, "today")
    start, end = get_period_range(period)
    return store.get_time_range("occupancy", start, end)


def _register_occ_kpis(app: object) -> None:
    """Update occupancy KPI cards."""

    @app.callback(
        Output("occ-kpi-grid", "children"),
        Input("occ-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_occ_kpis(time_range: str, _n: int, pathname: str | None) -> list:
        if pathname != "/occupancy":
            return no_update
        df = _get_occ_data(time_range)

        if df is None or df.empty:
            return [
                create_kpi_card("Current Occupancy", "—", icon="mdi:account-group"),
                create_kpi_card(
                    "Peak Today", "—", icon="mdi:chart-bell-curve-cumulative"
                ),
                create_kpi_card("Avg Utilization", "—", icon="mdi:chart-donut"),
                create_kpi_card("Busiest Zone", "—", icon="mdi:map-marker-check"),
            ]

        # Current: latest timestamp total
        latest_ts = df["timestamp"].max()
        latest = df[df["timestamp"] == latest_ts]
        current_total = int(latest["occupant_count"].sum())

        # Peak: max building-wide sum in period
        ts_totals = df.groupby("timestamp")["occupant_count"].sum()
        peak = int(ts_totals.max()) if not ts_totals.empty else 0

        # Avg utilization: mean of occupancy_ratio across zones
        monitored_ids = {z.id for z in get_monitored_zones()}
        mon_df = df[df["zone_id"].isin(monitored_ids)]
        avg_util = mon_df["occupancy_ratio"].mean() * 100 if not mon_df.empty else 0

        # Busiest zone: highest avg occupancy_ratio
        if not mon_df.empty:
            zone_avg = mon_df.groupby("zone_id")["occupancy_ratio"].mean()
            busiest_id = zone_avg.idxmax()
            z = get_zone_by_id(busiest_id)
            busiest_name = z.name if z else busiest_id
            # Shorten if needed
            if len(busiest_name) > 16:
                busiest_name = busiest_name[:14] + "…"
        else:
            busiest_name = "—"

        return [
            create_kpi_card(
                "Current Occupancy",
                str(current_total),
                unit="people",
                icon="mdi:account-group",
            ),
            create_kpi_card(
                "Peak Today",
                str(peak),
                unit="people",
                icon="mdi:chart-bell-curve-cumulative",
            ),
            create_kpi_card(
                "Avg Utilization",
                f"{avg_util:.0f}",
                unit="%",
                icon="mdi:chart-donut",
            ),
            create_kpi_card(
                "Busiest Zone",
                busiest_name,
                icon="mdi:map-marker-check",
            ),
        ]


def _register_occ_timeline(app: object) -> None:
    """Occupancy timeline with expected baseline and shift bands."""

    @app.callback(
        Output("occ-chart-timeline", "figure"),
        Input("occ-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_occ_timeline(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/occupancy":
            return no_update
        df = _get_occ_data(time_range)
        if df is None or df.empty:
            return empty_chart("No occupancy data available")

        # Aggregate building-wide by 15-min
        building_occ = (
            df.groupby(pd.Grouper(key="timestamp", freq="15min"))["occupant_count"]
            .sum()
            .reset_index()
        )
        building_occ = building_occ.dropna()

        if building_occ.empty:
            return empty_chart("No occupancy timeline data")

        fig = go.Figure()

        # Shift bands (only for "today" view)
        if time_range == "today" and not building_occ.empty:
            day = building_occ["timestamp"].dt.date.iloc[0]
            for start_h, end_h, label, color in [
                (6, 14, "Morning", "rgba(0, 113, 227, 0.04)"),
                (14, 22, "Afternoon", "rgba(52, 199, 89, 0.04)"),
            ]:
                fig.add_vrect(
                    x0=pd.Timestamp(day) + pd.Timedelta(hours=start_h),
                    x1=pd.Timestamp(day) + pd.Timedelta(hours=end_h),
                    fillcolor=color,
                    line_width=0,
                    annotation_text=label,
                    annotation_position="top left",
                    annotation_font_size=10,
                    annotation_font_color=TEXT_TERTIARY,
                )

        # Expected baseline
        full_occ = store.get("occupancy")
        if full_occ is not None and not full_occ.empty:
            tod = compute_time_of_day_baseline(full_occ, "occupant_count")
            if not tod.empty:
                # Map baseline to timeline
                building_occ["hour"] = building_occ["timestamp"].dt.hour
                building_occ["dow"] = building_occ["timestamp"].dt.dayofweek

                merge_cols = (
                    ["hour", "day_of_week"]
                    if "day_of_week" in tod.columns
                    else ["hour"]
                )
                bl = building_occ.merge(
                    tod,
                    left_on=["hour"]
                    + (["dow"] if "day_of_week" in tod.columns else []),
                    right_on=merge_cols,
                    how="left",
                )
                n_zones = df["zone_id"].nunique()
                bl["expected"] = bl.get("mean", 0) * n_zones

                fig.add_trace(
                    go.Scatter(
                        x=bl["timestamp"],
                        y=bl["expected"],
                        mode="lines",
                        name="Expected",
                        line=dict(color=TEXT_TERTIARY, width=1.5, dash="dash"),
                    )
                )

        # Actual line
        fig.add_trace(
            go.Scatter(
                x=building_occ["timestamp"],
                y=building_occ["occupant_count"],
                mode="lines",
                name="Actual",
                line=dict(color=ACCENT_BLUE, width=2),
            )
        )

        fig.update_yaxes(title_text="People")
        return apply_chart_theme(fig, "Occupancy Timeline")


def _register_occ_heatmap(app: object) -> None:
    """Zone utilization heatmap (zones × hours)."""

    @app.callback(
        Output("occ-chart-heatmap", "figure"),
        Input("occ-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_occ_heatmap(time_range: str, _n: int, pathname: str | None) -> go.Figure:
        if pathname != "/occupancy":
            return no_update
        df = _get_occ_data(time_range)
        if df is None or df.empty:
            return empty_chart("No occupancy data available")

        df = df.copy()
        df["hour"] = df["timestamp"].dt.hour

        # Only zones with capacity
        monitored = get_monitored_zones()
        cap_zones = [z for z in monitored if z.capacity > 0]
        cap_ids = {z.id for z in cap_zones}
        df = df[df["zone_id"].isin(cap_ids)]

        if df.empty:
            return empty_chart("No zone utilization data")

        pivot = df.pivot_table(
            values="occupancy_ratio",
            index="zone_id",
            columns="hour",
            aggfunc="mean",
        ).fillna(0)

        # Convert to percentage
        pivot_pct = (pivot * 100).round(1)

        zone_names = []
        for zid in pivot_pct.index:
            z = get_zone_by_id(zid)
            zone_names.append(z.name if z else zid)

        fig = go.Figure(
            go.Heatmap(
                z=pivot_pct.values,
                x=[f"{h:02d}:00" for h in pivot_pct.columns],
                y=zone_names,
                colorscale=UTILIZATION_COLORSCALE,
                zmin=0,
                zmax=100,
                colorbar=dict(title="% Capacity"),
                hovertemplate=("%{y}<br>%{x}: %{z:.0f}%<extra></extra>"),
            )
        )

        return apply_chart_theme(fig, "Zone Utilization (% Capacity)", height=420)


def _register_occ_sankey(app: object) -> None:
    """People flow Sankey diagram between zones."""

    @app.callback(
        Output("occ-chart-sankey", "figure"),
        Input("occ-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_occ_sankey(time_range: str, _n: int, pathname: str | None) -> go.Figure:
        if pathname != "/occupancy":
            return no_update
        df = _get_occ_data(time_range)
        if df is None or df.empty:
            return empty_chart("No occupancy data for flow analysis")

        # Only zones with capacity
        monitored = get_monitored_zones()
        cap_zones = [z for z in monitored if z.capacity > 0]
        cap_ids = {z.id for z in cap_zones}
        df = df[df["zone_id"].isin(cap_ids)].copy()

        if df.empty:
            return empty_chart("No zone flow data")

        # Compute occupancy deltas per zone per timestamp
        df = df.sort_values(["zone_id", "timestamp"])
        df["delta"] = df.groupby("zone_id")["occupant_count"].diff()
        df = df.dropna(subset=["delta"])

        # For each timestamp, find sources (delta < 0) and sinks (delta > 0)
        flows: dict[tuple[str, str], float] = defaultdict(float)

        for ts, group in df.groupby("timestamp"):
            sources = group[group["delta"] < -1]
            sinks = group[group["delta"] > 1]

            if sources.empty or sinks.empty:
                continue

            total_out = abs(sources["delta"].sum())
            total_in = sinks["delta"].sum()

            if total_out == 0 or total_in == 0:
                continue

            # Distribute proportionally
            for _, src in sources.iterrows():
                for _, snk in sinks.iterrows():
                    weight = (
                        abs(src["delta"])
                        / total_out
                        * snk["delta"]
                        / total_in
                        * min(total_out, total_in)
                    )
                    if weight > 0.1:
                        flows[(src["zone_id"], snk["zone_id"])] += weight

        if not flows:
            return empty_chart("Insufficient movement data for flow diagram")

        # Keep top 15 edges
        sorted_flows = sorted(flows.items(), key=lambda x: x[1], reverse=True)
        top_flows = sorted_flows[:15]

        # Build node and link lists
        all_zones = set()
        for (src, tgt), _ in top_flows:
            all_zones.add(src)
            all_zones.add(tgt)

        zone_list = sorted(all_zones)
        zone_idx = {z: i for i, z in enumerate(zone_list)}
        zone_labels = []
        for zid in zone_list:
            z = get_zone_by_id(zid)
            name = z.name if z else zid
            zone_labels.append(name[:18])

        src_indices = [zone_idx[s] for (s, _), _ in top_flows]
        tgt_indices = [zone_idx[t] for (_, t), _ in top_flows]
        values = [round(v, 1) for _, v in top_flows]

        # Node colors
        n_nodes = len(zone_list)
        node_colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(n_nodes)]

        fig = go.Figure(
            go.Sankey(
                node=dict(
                    label=zone_labels,
                    color=node_colors,
                    pad=20,
                    thickness=20,
                ),
                link=dict(
                    source=src_indices,
                    target=tgt_indices,
                    value=values,
                    color=["rgba(0, 113, 227, 0.2)" for _ in values],
                ),
            )
        )

        fig.update_layout(
            title=dict(text="People Flow Between Zones", font=dict(size=15)),
            height=360,
            margin=dict(l=24, r=24, t=48, b=24),
        )
        return fig


def _register_occ_efficiency(app: object) -> None:
    """Space efficiency horizontal bar chart by zone."""

    @app.callback(
        Output("occ-chart-efficiency", "figure"),
        Input("occ-time-range", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_occ_efficiency(
        time_range: str, _n: int, pathname: str | None
    ) -> go.Figure:
        if pathname != "/occupancy":
            return no_update
        df = _get_occ_data(time_range)
        if df is None or df.empty:
            return empty_chart("No occupancy data available")

        # Only zones with capacity, during business hours
        monitored = get_monitored_zones()
        cap_zones = [z for z in monitored if z.capacity > 0]
        cap_ids = {z.id for z in cap_zones}
        df = df[df["zone_id"].isin(cap_ids)]

        # Filter to business hours (6-22)
        df = df[(df["timestamp"].dt.hour >= 6) & (df["timestamp"].dt.hour < 22)]

        if df.empty:
            return empty_chart("No business hours occupancy data")

        # Mean occupancy ratio per zone
        zone_util = df.groupby("zone_id")["occupancy_ratio"].mean().reset_index()
        zone_util["pct"] = (zone_util["occupancy_ratio"] * 100).round(1)

        # Add zone names
        zone_util["name"] = zone_util["zone_id"].apply(
            lambda zid: get_zone_by_id(zid).name if get_zone_by_id(zid) else zid
        )

        # Sort ascending
        zone_util = zone_util.sort_values("pct", ascending=True)

        # Color: <30% orange, 30-90% healthy, >90% red
        colors = []
        for pct in zone_util["pct"]:
            if pct > 90:
                colors.append(STATUS_CRITICAL)
            elif pct < 30:
                colors.append(STATUS_WARNING)
            else:
                colors.append(STATUS_HEALTHY)

        fig = go.Figure(
            go.Bar(
                x=zone_util["pct"],
                y=zone_util["name"],
                orientation="h",
                marker=dict(color=colors),
                text=zone_util["pct"].apply(lambda v: f"{v:.0f}%"),
                textposition="outside",
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            )
        )

        # Threshold reference lines
        fig.add_vline(
            x=30,
            line_dash="dot",
            line_color=STATUS_WARNING,
            annotation_text="Underutilized",
            annotation_font_size=10,
        )
        fig.add_vline(
            x=90,
            line_dash="dot",
            line_color=STATUS_CRITICAL,
            annotation_text="Overcrowded",
            annotation_font_size=10,
        )

        fig.update_xaxes(title_text="Utilization (%)", range=[0, 110])
        return apply_chart_theme(fig, "Space Efficiency by Zone", height=420)
