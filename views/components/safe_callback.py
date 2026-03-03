"""Safe callback decorator for Dash applications.

Catches all exceptions in Dash callbacks, logs them to the terminal,
and returns dash.no_update or an empty styled Plotly figure instead of
crashing the UI. NEVER let an exception propagate to the browser.
"""

from __future__ import annotations

import functools
from typing import Any

import plotly.graph_objects as go
from dash import no_update
from loguru import logger

from config.theme import TEXT_TERTIARY


def _empty_figure(message: str = "No data available") -> go.Figure:
    """Create a clean empty Plotly figure with a centered message.

    Args:
        message: Text to display in the empty state.

    Returns:
        A styled empty Plotly figure.
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
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


def safe_callback(func: Any = None, *, default: Any = None) -> Any:
    """Decorator that wraps a Dash callback in a try/except.

    Catches ALL exceptions, logs them with loguru, and returns either:
    - The provided `default` value
    - dash.no_update (if no default specified)

    Can be used with or without arguments:
        @safe_callback
        def my_callback(...): ...

        @safe_callback(default=_empty_figure())
        def my_chart_callback(...): ...

    Args:
        func: The callback function (when used without arguments).
        default: Value to return on error. Defaults to dash.no_update.

    Returns:
        Wrapped function that never raises.
    """

    def decorator(fn: Any) -> Any:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error in {fn.__name__}: {e}")
                if default is not None:
                    return default
                return no_update

        return wrapper

    if func is not None:
        # Used as @safe_callback without parentheses
        return decorator(func)
    # Used as @safe_callback(default=...)
    return decorator
