"""Shared chart theming and component helpers.

Provides consistent Plotly figure styling and reusable chart
container components for all detail pages.
"""

from __future__ import annotations

import copy

import plotly.graph_objects as go
from dash import dcc, html

from config.theme import (
    ACCENT_BLUE,
    CHART_TEMPLATE,
    FONT_STACK,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_TERTIARY,
)

# ── Color Scales ─────────────────────────────
HEATMAP_COLORSCALE = [
    [0.0, "#E1F0FF"],
    [0.5, ACCENT_BLUE],
    [1.0, "#001752"],
]

COMFORT_COLORSCALE = [
    [0.0, STATUS_CRITICAL],
    [0.5, STATUS_WARNING],
    [1.0, STATUS_HEALTHY],
]

UTILIZATION_COLORSCALE = [
    [0.0, "#F2F2F7"],
    [0.3, "#E1F0FF"],
    [0.7, ACCENT_BLUE],
    [0.9, STATUS_WARNING],
    [1.0, STATUS_CRITICAL],
]

# ── Graph config for all detail page charts ──
GRAPH_CONFIG: dict = {
    "displaylogo": False,
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {"format": "svg", "filename": "plantaos_chart"},
}


def apply_chart_theme(
    fig: go.Figure,
    title: str = "",
    height: int = 360,
) -> go.Figure:
    """Apply the PlantaOS chart theme to a Plotly figure.

    Args:
        fig: Plotly figure to style.
        title: Optional chart title.
        height: Chart height in pixels.

    Returns:
        The same figure with theme applied.
    """
    layout = copy.deepcopy(CHART_TEMPLATE["layout"])
    layout["height"] = height
    if title:
        layout["title"] = {"text": title, "font": {"size": 15}}
    fig.update_layout(**layout)
    return fig


def empty_chart(
    message: str = "No data available",
    height: int = 360,
) -> go.Figure:
    """Create a blank chart with a centered message.

    Args:
        message: Text to display.
        height: Chart height in pixels.

    Returns:
        Empty Plotly figure with annotation.
    """
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(
                    family=FONT_STACK,
                    size=14,
                    color=TEXT_TERTIARY,
                ),
            )
        ],
    )
    return fig


def chart_card(graph_id: str, title: str) -> html.Div:
    """Wrap a dcc.Graph in a themed card with loading state.

    Args:
        graph_id: ID for the dcc.Graph component.
        title: Chart title text.

    Returns:
        html.Div containing the chart card.
    """
    return html.Div(
        [
            html.Div(title, className="chart-title"),
            dcc.Loading(
                type="dot",
                color=ACCENT_BLUE,
                children=[
                    dcc.Graph(
                        id=graph_id,
                        config=GRAPH_CONFIG,
                        style={"height": "360px"},
                    ),
                ],
            ),
        ],
        className="chart-container",
    )


# ── Time range mapping ───────────────────────
TIME_RANGE_MAP: dict[str, str] = {
    "today": "today",
    "7d": "last_7d",
    "30d": "last_30d",
}
