"""Data Explorer page callbacks.

Registers callbacks for the data table, chart preview, and CSV export
on the Data Explorer page. Data flows from the DataStore through
dataset/zone/time-range filtering to an HTML table and Plotly line chart.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update
from loguru import logger

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    BG_HOVER,
    BORDER_LIGHT,
    FONT_STACK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.safe_callback import safe_callback


def _filter_dataframe(
    dataset_name: str, zone: str | None, time_range: str
) -> pd.DataFrame:
    """Fetch and filter a dataset from the store.

    Args:
        dataset_name: Key in the DataStore (e.g. 'comfort', 'energy').
        zone: Optional zone_id to filter by, or None for all zones.
        time_range: One of '1d', '7d', '30d'.

    Returns:
        Filtered DataFrame (may be empty).
    """
    from data.store import store

    df = store.get(dataset_name)
    if df is None or df.empty:
        return pd.DataFrame()

    # Zone filter
    if zone and "zone_id" in df.columns:
        df = df[df["zone_id"] == zone]

    # Time range filter
    if "timestamp" in df.columns:
        now = pd.Timestamp.now()
        days_map = {"1d": 1, "7d": 7, "30d": 30}
        days = days_map.get(time_range, 7)
        cutoff = now - pd.Timedelta(days=days)
        df = df[df["timestamp"] >= cutoff]

    return df.reset_index(drop=True)


def _build_table(df: pd.DataFrame) -> html.Table:
    """Build a styled HTML table from the first 100 rows of a DataFrame.

    Args:
        df: Source DataFrame.

    Returns:
        Dash html.Table component.
    """
    if df.empty:
        return html.Div(
            "No data available for the selected filters.",
            style={
                "color": TEXT_TERTIARY,
                "fontFamily": FONT_STACK,
                "fontSize": "14px",
                "padding": "24px",
                "textAlign": "center",
            },
        )

    columns = list(df.columns)
    display_df = df.head(100)

    # Header row
    header = html.Thead(
        html.Tr(
            [
                html.Th(
                    col,
                    style={
                        "color": TEXT_PRIMARY,
                        "fontWeight": 600,
                        "fontSize": "13px",
                        "fontFamily": FONT_STACK,
                        "padding": "10px 12px",
                        "textAlign": "left",
                        "borderBottom": f"2px solid {BORDER_LIGHT}",
                        "whiteSpace": "nowrap",
                    },
                )
                for col in columns
            ]
        )
    )

    # Data rows with alternating background
    rows = []
    for i, (_, row) in enumerate(display_df.iterrows()):
        bg = BG_HOVER if i % 2 == 1 else BG_CARD
        cells = [
            html.Td(
                str(row[col]),
                style={
                    "color": TEXT_SECONDARY,
                    "fontSize": "12px",
                    "fontFamily": FONT_STACK,
                    "padding": "8px 12px",
                    "borderBottom": f"1px solid {BORDER_LIGHT}",
                    "whiteSpace": "nowrap",
                },
            )
            for col in columns
        ]
        rows.append(html.Tr(cells, style={"background": bg}))

    body = html.Tbody(rows)

    return html.Table(
        [header, body],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontFamily": FONT_STACK,
        },
    )


def _build_chart(df: pd.DataFrame) -> go.Figure:
    """Build a line chart of the first numeric column over time.

    Args:
        df: Source DataFrame (must contain 'timestamp' and at least one
            numeric column).

    Returns:
        Plotly Figure with PlantaOS styling.
    """
    fig = go.Figure()

    if df.empty or "timestamp" not in df.columns:
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 14, "color": TEXT_TERTIARY},
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis={"visible": False},
            yaxis={"visible": False},
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
        )
        return fig

    # Find the first numeric column that is not 'timestamp'
    numeric_cols = [
        c for c in df.select_dtypes(include=["number"]).columns if c != "timestamp"
    ]
    if not numeric_cols:
        fig.add_annotation(
            text="No numeric columns to chart",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 14, "color": TEXT_TERTIARY},
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis={"visible": False},
            yaxis={"visible": False},
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
        )
        return fig

    col = numeric_cols[0]
    sorted_df = df.sort_values("timestamp")

    fig.add_trace(
        go.Scatter(
            x=sorted_df["timestamp"],
            y=sorted_df[col],
            mode="lines",
            name=col,
            line={"color": ACCENT_BLUE, "width": 2},
            hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT_STACK, "color": TEXT_PRIMARY, "size": 13},
        title={
            "text": col.replace("_", " ").title(),
            "font": {"size": 15, "color": TEXT_PRIMARY},
        },
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showline": True,
            "linecolor": BORDER_LIGHT,
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showline": False,
        },
        margin={"l": 48, "r": 24, "t": 48, "b": 40},
        showlegend=False,
    )

    return fig


def register_data_explorer_callbacks(app: object) -> None:
    """Register all Data Explorer page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_table_and_chart(app)
    _register_csv_export(app)


def _register_table_and_chart(app: object) -> None:
    """Update the data table and chart based on filter selections."""

    @app.callback(
        Output("data-explorer-table", "children"),
        Output("data-explorer-chart", "figure"),
        Input("data-explorer-dataset", "value"),
        Input("data-explorer-zone", "value"),
        Input("data-explorer-range", "value"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_table_and_chart(
        dataset_name: str,
        zone: str | None,
        time_range: str,
        pathname: str | None,
    ) -> tuple:
        if pathname != "/view_data":
            return no_update, no_update

        logger.debug(
            f"Data Explorer: dataset={dataset_name}, zone={zone}, range={time_range}"
        )

        df = _filter_dataframe(dataset_name, zone, time_range)
        table = _build_table(df)
        chart = _build_chart(df)

        return table, chart


def _register_csv_export(app: object) -> None:
    """Export filtered data as a CSV download."""

    @app.callback(
        Output("data-explorer-download", "data"),
        Input("data-explorer-export-btn", "n_clicks"),
        State("data-explorer-dataset", "value"),
        State("data-explorer-zone", "value"),
        State("data-explorer-range", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def export_csv(
        n_clicks: int | None,
        dataset_name: str,
        zone: str | None,
        time_range: str,
        pathname: str | None,
    ) -> dict | None:
        if pathname != "/view_data":
            return no_update

        logger.info(
            f"Data Explorer CSV export: dataset={dataset_name}, "
            f"zone={zone}, range={time_range}"
        )

        df = _filter_dataframe(dataset_name, zone, time_range)
        if df.empty:
            return no_update

        return dcc.send_data_frame(df.to_csv, "plantaos_data_export.csv", index=False)
