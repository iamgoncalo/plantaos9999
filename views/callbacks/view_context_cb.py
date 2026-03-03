"""Context view callbacks — weather data population."""

from __future__ import annotations

from dash import Input, Output, html
from dash_iconify import DashIconify
from loguru import logger

from config.theme import (
    FONT_DATA_STACK,
    FONT_SIZE_SM,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from data.store import store
from views.components.safe_callback import safe_callback


def register_context_callbacks(app: object) -> None:
    """Register callbacks for the context view page.

    Args:
        app: The Dash application instance.
    """
    _register_weather_card(app)


def _register_weather_card(app: object) -> None:
    """Populate weather card from synthetic weather data."""

    @app.callback(
        Output("context-weather-card", "children"),
        Input("building-state-store", "data"),
    )
    @safe_callback
    def update_weather(state_data: dict | None) -> list:
        """Read latest weather from data store and render card contents.

        Args:
            state_data: Current building state dict (used as trigger).

        Returns:
            List of Dash components for the weather card.
        """
        weather_df = store.get("weather")

        if weather_df.empty:
            logger.debug("No weather data available for context view")
            return [
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:weather-cloudy-alert",
                            width=20,
                            color=TEXT_TERTIARY,
                        ),
                        html.Span(
                            "No weather data available",
                            style={"fontSize": FONT_SIZE_SM, "color": TEXT_TERTIARY},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "padding": "16px 20px",
                    },
                ),
            ]

        # Get the most recent weather reading
        latest = weather_df.sort_values("timestamp").iloc[-1]
        temp_c = latest.get("outdoor_temp_c", 0.0)
        humidity_pct = latest.get("outdoor_humidity_pct", 0.0)
        is_raining = bool(latest.get("is_raining", False))
        wind_ms = latest.get("wind_speed_ms", 0.0)

        condition = "Raining" if is_raining else "Clear"
        condition_icon = "mdi:weather-rainy" if is_raining else "mdi:weather-sunny"

        return [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:weather-partly-cloudy",
                        width=20,
                        color=TEXT_SECONDARY,
                    ),
                    html.Span(
                        "Current Outdoor Conditions",
                        style={
                            "fontSize": "15px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginBottom": "12px",
                },
            ),
            html.Div(
                [
                    _weather_metric(
                        "mdi:thermometer",
                        "Temperature",
                        f"{temp_c:.1f} °C",
                    ),
                    _weather_metric(
                        "mdi:water-percent",
                        "Humidity",
                        f"{humidity_pct:.0f}%",
                    ),
                    _weather_metric(
                        condition_icon,
                        "Conditions",
                        condition,
                    ),
                    _weather_metric(
                        "mdi:weather-windy",
                        "Wind",
                        f"{wind_ms:.1f} m/s",
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))",
                    "gap": "16px",
                },
            ),
        ]


def _weather_metric(icon: str, label: str, value: str) -> html.Div:
    """Create a single weather metric display.

    Args:
        icon: Dash-iconify icon identifier.
        label: Metric label text.
        value: Metric value text.

    Returns:
        Dash html.Div containing the metric display.
    """
    return html.Div(
        [
            DashIconify(icon=icon, width=16, color=TEXT_SECONDARY),
            html.Div(
                [
                    html.Span(
                        label,
                        style={"fontSize": FONT_SIZE_SM, "color": TEXT_TERTIARY},
                    ),
                    html.Span(
                        value,
                        style={
                            "fontSize": "15px",
                            "fontWeight": 500,
                            "fontFamily": FONT_DATA_STACK,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "2px",
                },
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "flex-start",
            "gap": "8px",
        },
    )
