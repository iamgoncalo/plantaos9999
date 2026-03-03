"""4D Time Explorer page: temporal floorplan with playback controls.

Renders an animated floorplan that lets users scrub through 30 days of
building metrics at 15-minute resolution. Distinct from the /simulation
optimization page — this is a pure observation/exploration tool.
"""

from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    FONT_STACK,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from views.components.kpi_card import create_kpi_skeleton


def create_view_4d_page() -> html.Div:
    """Create the 4D Time Explorer page layout.

    Returns:
        Dash html.Div containing the temporal floorplan with time
        slider, playback controls, metric selectors, and KPI strip.
    """
    # ── Page header ────────────────────────────
    page_header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:clock-fast",
                        width=28,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "4D Time Explorer",
                        style={
                            "margin": 0,
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                },
            ),
            html.P(
                "Explore building metrics across time",
                style={
                    "margin": "8px 0 0",
                    "color": TEXT_SECONDARY,
                    "fontSize": "14px",
                    "maxWidth": "640px",
                },
            ),
        ],
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    # ── Metric selector ───────────────────────
    metric_selector = dcc.RadioItems(
        id="view4d-metric",
        options=[
            {"label": "Zone Performance", "value": "freedom_index"},
            {"label": "Temperature", "value": "temperature_c"},
            {"label": "CO2", "value": "co2_ppm"},
            {"label": "Energy", "value": "total_energy_kwh"},
            {"label": "Occupancy", "value": "occupant_count"},
        ],
        value="temperature_c",
        className="time-range-selector",
        inline=True,
    )

    # ── Floor selector ─────────────────────────
    floor_selector = dcc.RadioItems(
        id="view4d-floor",
        options=[
            {"label": "Piso 0", "value": "0"},
            {"label": "Piso 1", "value": "1"},
        ],
        value="0",
        className="time-range-selector",
        inline=True,
    )

    # ── Controls row ───────────────────────────
    controls_row = html.Div(
        [metric_selector, floor_selector],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "24px",
            "marginBottom": f"{GAP_ELEMENT}px",
            "flexWrap": "wrap",
        },
    )

    # ── Time slider ────────────────────────────
    time_slider = html.Div(
        dcc.Slider(
            id="view4d-time-slider",
            min=0,
            max=2879,
            step=1,
            value=0,
            marks={
                0: "Day 1",
                480: "Day 6",
                960: "Day 11",
                1440: "Day 16",
                1920: "Day 21",
                2400: "Day 26",
                2879: "Day 30",
            },
            tooltip={"placement": "bottom", "always_visible": True},
        ),
        style={
            "padding": f"0 {PADDING_CARD}px",
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    # ── Playback controls ──────────────────────
    play_btn = html.Button(
        DashIconify(icon="mdi:play", width=22, color=TEXT_PRIMARY),
        id="view4d-play-btn",
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "width": "40px",
            "height": "40px",
            "borderRadius": "50%",
            "border": "none",
            "background": BG_CARD,
            "boxShadow": CARD_SHADOW,
            "cursor": "pointer",
        },
    )

    speed_selector = dcc.RadioItems(
        id="view4d-speed",
        options=[
            {"label": "1x", "value": "1x"},
            {"label": "2x", "value": "2x"},
            {"label": "5x", "value": "5x"},
            {"label": "10x", "value": "10x"},
        ],
        value="2x",
        className="time-range-selector",
        inline=True,
    )

    timestamp_display = html.Span(
        id="view4d-timestamp-display",
        style={
            "fontFamily": FONT_STACK,
            "fontSize": "14px",
            "fontWeight": 500,
            "color": TEXT_TERTIARY,
            "marginLeft": "auto",
        },
    )

    playback_row = html.Div(
        [play_btn, speed_selector, timestamp_display],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": f"{GAP_ELEMENT}px",
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    # ── Interval + Store for playback state ────
    play_interval = dcc.Interval(
        id="view4d-play-interval",
        interval=500,
        disabled=True,
        n_intervals=0,
    )
    playing_store = dcc.Store(id="view4d-playing", data=False)

    # ── Floorplan graph ────────────────────────
    floorplan = html.Div(
        dcc.Graph(
            id="view4d-floorplan",
            config={"displayModeBar": False},
            style={"height": "520px"},
        ),
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "padding": f"{PADDING_CARD}px",
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    # ── Metric summary strip (4 KPI skeletons) ─
    metric_strip = html.Div(
        id="view4d-metric-strip",
        className="grid-4",
        children=[create_kpi_skeleton() for _ in range(4)],
    )

    return html.Div(
        [
            page_header,
            controls_row,
            time_slider,
            playback_row,
            play_interval,
            playing_store,
            floorplan,
            metric_strip,
        ],
        className="page-enter",
    )
