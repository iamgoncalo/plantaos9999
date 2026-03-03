"""Callbacks for the Flow visualization page — Sankey diagram of zone transitions."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, no_update
from loguru import logger

from config.building import get_monitored_zones, get_zone_by_id
from config.theme import BG_CARD, FONT_STACK, TEXT_PRIMARY
from data.store import store
from views.components.safe_callback import safe_callback


def register_flow_callbacks(app: object) -> None:
    """Register Flow page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_sankey(app)


def _register_sankey(app: object) -> None:
    """Render Sankey diagram from occupancy transitions."""

    @app.callback(
        Output("flow-sankey-graph", "figure"),
        Input("url", "pathname"),
        Input("flow-floor-select", "value"),
        Input("flow-time-select", "value"),
    )
    @safe_callback
    def update_sankey(
        pathname: str,
        floor_filter: str,
        time_range: str,
    ) -> go.Figure:
        """Build Sankey diagram of zone-to-zone flows."""
        if pathname != "/view_flow":
            return no_update

        try:
            df = store.get("occupancy")
            if df is None or df.empty:
                return _empty_figure("No occupancy data available")

            # Filter by time range
            df = _filter_by_time(df, time_range)
            if df.empty:
                return _empty_figure("No data for selected time range")

            # Get canonical zones
            zones = get_monitored_zones()
            zone_ids = {z.id for z in zones}

            # Filter by floor if needed
            if floor_filter != "all":
                floor_num = int(floor_filter)
                zone_ids = {z.id for z in zones if z.floor == floor_num}

            # Filter df to only include relevant zones
            df = df[df["zone_id"].isin(zone_ids)]
            if df.empty:
                return _empty_figure("No zone data for selected floor")

            # Compute transitions: for each timestamp, look at which zones
            # have occupancy changes suggesting movement
            flows = _compute_flows(df, zone_ids)

            if not flows:
                return _empty_figure("No significant flow patterns detected")

            # Build Sankey data
            zone_list = sorted(zone_ids)
            zone_idx = {z: i for i, z in enumerate(zone_list)}
            labels = []
            for z in zone_list:
                zi = get_zone_by_id(z)
                labels.append(zi.name if zi else z)

            sources = []
            targets = []
            values = []
            for (src, tgt), count in flows.items():
                if src in zone_idx and tgt in zone_idx and count > 0:
                    sources.append(zone_idx[src])
                    targets.append(zone_idx[tgt])
                    values.append(count)

            if not values:
                return _empty_figure("No flow data to display")

            fig = go.Figure(
                go.Sankey(
                    arrangement="snap",
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="#E5E5EA", width=0.5),
                        label=labels,
                        color="#0071E3",
                    ),
                    link=dict(
                        source=sources,
                        target=targets,
                        value=values,
                        color="rgba(0, 113, 227, 0.15)",
                    ),
                )
            )

            fig.update_layout(
                font=dict(family=FONT_STACK, size=12, color=TEXT_PRIMARY),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=BG_CARD,
                margin=dict(l=16, r=16, t=40, b=16),
                title=dict(
                    text="Zone-to-Zone Occupancy Flow",
                    font=dict(size=15, family=FONT_STACK),
                    x=0.02,
                ),
            )

            return fig

        except Exception as e:
            logger.warning(f"Flow Sankey error: {e}")
            return _empty_figure("Error computing flow data")


def _filter_by_time(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Filter dataframe by time range string."""
    if "timestamp" not in df.columns:
        return df

    now = pd.Timestamp.now()
    hours_map = {"24h": 24, "7d": 168, "30d": 720}
    hours = hours_map.get(time_range, 24)

    cutoff = now - pd.Timedelta(hours=hours)
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    return df[ts >= cutoff]


def _compute_flows(
    df: pd.DataFrame,
    zone_ids: set[str],
) -> dict[tuple[str, str], int]:
    """Compute zone-to-zone transition counts from occupancy data.

    Uses consecutive timestamps: when occupancy decreases in zone A
    and increases in zone B at the same time, we count a flow A->B.
    """
    flows: dict[tuple[str, str], int] = {}

    if "timestamp" not in df.columns or "zone_id" not in df.columns:
        return flows

    occ_col = "occupant_count" if "occupant_count" in df.columns else None
    if occ_col is None:
        return flows

    # Group by timestamp and zone
    grouped = df.groupby(["timestamp", "zone_id"])[occ_col].sum().unstack(fill_value=0)

    # Only keep zone_ids we care about
    valid_cols = [c for c in grouped.columns if c in zone_ids]
    if len(valid_cols) < 2:
        return flows

    grouped = grouped[valid_cols].sort_index()

    # Compute deltas between consecutive timestamps
    deltas = grouped.diff().dropna()

    for _, row in deltas.iterrows():
        decreasing = [z for z in valid_cols if row[z] < 0]
        increasing = [z for z in valid_cols if row[z] > 0]

        for src in decreasing:
            for tgt in increasing:
                if src != tgt:
                    flow_amount = min(abs(row[src]), row[tgt])
                    if flow_amount > 0:
                        key = (src, tgt)
                        flows[key] = flows.get(key, 0) + int(flow_amount)

    # Keep only significant flows (top N)
    if flows:
        threshold = max(1, max(flows.values()) // 20)
        flows = {k: v for k, v in flows.items() if v >= threshold}

    return flows


def _empty_figure(message: str) -> go.Figure:
    """Create an empty figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#86868B", family=FONT_STACK),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BG_CARD,
        margin=dict(l=16, r=16, t=16, b=16),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
