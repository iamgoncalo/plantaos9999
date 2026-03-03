"""Callbacks for the Heatmap visualization page — zone x hour matrix."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, no_update
from loguru import logger

from config.building import get_zones_by_floor
from config.theme import BG_CARD, FONT_STACK, TEXT_PRIMARY
from data.store import store
from views.components.safe_callback import safe_callback

# Metric display names and colorscales
_METRIC_CONFIG: dict[str, dict] = {
    "temperature_c": {
        "label": "Temperature (°C)",
        "colorscale": "RdYlBu_r",
        "dataset": "comfort",
        "unit": "°C",
    },
    "co2_ppm": {
        "label": "CO2 (ppm)",
        "colorscale": "YlOrRd",
        "dataset": "comfort",
        "unit": "ppm",
    },
    "humidity_pct": {
        "label": "Humidity (%)",
        "colorscale": "Blues",
        "dataset": "comfort",
        "unit": "%",
    },
    "occupant_count": {
        "label": "Occupancy",
        "colorscale": "Purples",
        "dataset": "occupancy",
        "unit": "people",
    },
    "total_kwh": {
        "label": "Energy (kWh)",
        "colorscale": "Oranges",
        "dataset": "energy",
        "unit": "kWh",
    },
}


def register_heatmap_callbacks(app: object) -> None:
    """Register Heatmap page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_heatmap_chart(app)


def _register_heatmap_chart(app: object) -> None:
    """Render zone x hour heatmap for selected metric."""

    @app.callback(
        Output("heatmap-chart", "figure"),
        Input("url", "pathname"),
        Input("heatmap-metric-select", "value"),
        Input("heatmap-floor-select", "value"),
    )
    @safe_callback
    def update_heatmap(
        pathname: str,
        metric: str,
        floor: int,
    ) -> go.Figure:
        """Build heatmap figure."""
        if pathname != "/view_heatmap":
            return no_update

        try:
            config = _METRIC_CONFIG.get(metric)
            if not config:
                return _empty_figure("Unknown metric selected")

            dataset_name = config["dataset"]
            df = store.get(dataset_name)
            if df is None or df.empty:
                return _empty_figure(f"No {dataset_name} data available")

            # Get zones for the selected floor
            zones = get_zones_by_floor(floor)
            canonical_zones = [z for z in zones if getattr(z, "canonical", True)]
            if not canonical_zones:
                return _empty_figure("No zones for selected floor")

            zone_ids = [z.id for z in canonical_zones]
            zone_names = [z.name for z in canonical_zones]

            # Filter to relevant zones
            if "zone_id" not in df.columns:
                return _empty_figure("No zone_id column in data")

            df_filtered = df[df["zone_id"].isin(zone_ids)].copy()
            if df_filtered.empty:
                return _empty_figure("No data for selected zones")

            # Determine the column to use
            col = metric
            if col not in df_filtered.columns:
                return _empty_figure(f"Column '{col}' not found in dataset")

            # Parse timestamps and extract hour
            df_filtered["timestamp"] = pd.to_datetime(
                df_filtered["timestamp"], errors="coerce"
            )
            df_filtered = df_filtered.dropna(subset=["timestamp"])
            df_filtered["hour"] = df_filtered["timestamp"].dt.hour

            # Pivot: zone x hour, with mean values
            pivot = df_filtered.pivot_table(
                values=col,
                index="zone_id",
                columns="hour",
                aggfunc="mean",
            )

            # Ensure all hours 0-23 are present
            for h in range(24):
                if h not in pivot.columns:
                    pivot[h] = np.nan
            pivot = pivot.reindex(columns=sorted(pivot.columns))

            # Reorder rows to match zone_ids order
            pivot = pivot.reindex(zone_ids)

            # Replace zone_ids with names for display
            zone_name_map = dict(zip(zone_ids, zone_names))
            pivot.index = [zone_name_map.get(z, z) for z in pivot.index]

            fig = go.Figure(
                go.Heatmap(
                    z=pivot.values,
                    x=[f"{h:02d}:00" for h in range(24)],
                    y=list(pivot.index),
                    colorscale=config["colorscale"],
                    colorbar=dict(
                        title=dict(text=config["unit"], font=dict(size=11)),
                        thickness=12,
                        outlinewidth=0,
                    ),
                    hoverongaps=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Hour: %{x}<br>"
                        f"{config['label']}: %{{z:.1f}} {config['unit']}"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(
                title=dict(
                    text=f"{config['label']} — Piso {floor}",
                    font=dict(size=15, family=FONT_STACK),
                    x=0.02,
                ),
                font=dict(family=FONT_STACK, size=12, color=TEXT_PRIMARY),
                xaxis=dict(
                    title="Hour of Day",
                    dtick=1,
                    side="bottom",
                ),
                yaxis=dict(
                    title="",
                    autorange="reversed",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=BG_CARD,
                margin=dict(l=140, r=16, t=50, b=50),
            )

            return fig

        except Exception as e:
            logger.warning(f"Heatmap error: {e}")
            return _empty_figure("Error generating heatmap")


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
