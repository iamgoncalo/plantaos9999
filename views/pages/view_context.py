"""Context page — site environment and building information for CFT Aveiro."""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    FONT_DATA_STACK,
    FONT_SIZE_SM,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)


def create_context_page() -> html.Div:
    """Create the site context page with weather, map, and building info.

    Returns:
        Dash html.Div containing the context page layout.
    """
    header = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:earth",
                        width=24,
                        color=ACCENT_BLUE,
                    ),
                    html.H2(
                        "Context \u2014 Aveiro CFT Building",
                        style={
                            "margin": "0 0 0 8px",
                            "fontSize": "22px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
            ),
            html.Div(
                [
                    DashIconify(
                        icon="mdi:map-marker",
                        width=16,
                        color=TEXT_SECONDARY,
                    ),
                    html.Span(
                        "CFT HORSE/Renault \u2014 Aveiro, Portugal",
                        style={"fontSize": FONT_SIZE_SM, "color": TEXT_SECONDARY},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "6px",
                },
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    weather_card = html.Div(
        id="context-weather-card",
        children=[
            html.Div(
                [
                    DashIconify(
                        icon="mdi:weather-partly-cloudy",
                        width=20,
                        color=TEXT_TERTIARY,
                    ),
                    html.Span(
                        "Loading weather data\u2026",
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
        ],
        className="card",
        style={"marginBottom": f"{GAP_ELEMENT}px"},
    )

    map_card = html.Div(
        html.Iframe(
            src=(
                "https://www.openstreetmap.org/export/embed.html"
                "?bbox=-8.66,-8.64,40.635,40.645&layer=mapnik"
            ),
            style={
                "width": "100%",
                "height": "400px",
                "border": "none",
                "borderRadius": CARD_RADIUS,
            },
        ),
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "padding": f"{PADDING_CARD}px",
            "overflow": "hidden",
            "marginBottom": f"{GAP_ELEMENT}px",
        },
    )

    building_card = html.Div(
        [
            html.Div(
                [
                    DashIconify(
                        icon="mdi:office-building",
                        width=20,
                        color=ACCENT_BLUE,
                    ),
                    html.H3(
                        "CFT HORSE/Renault Building",
                        style={
                            "margin": "0 0 0 8px",
                            "fontSize": "17px",
                            "fontWeight": 600,
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "12px",
                },
            ),
            html.P(
                "The CFT (Centro de Forma\u00e7\u00e3o T\u00e9cnica) HORSE/Renault "
                "training building is located in Aveiro, Portugal. It serves as a "
                "technical training centre supporting up to 454 occupants across "
                "2 floors with a total area of approximately 800 m\u00b2.",
                style={
                    "fontSize": "14px",
                    "lineHeight": "1.6",
                    "color": TEXT_SECONDARY,
                    "marginBottom": "16px",
                },
            ),
            html.Div(
                [
                    _info_row("mdi:map-marker", "Address", "Aveiro, Portugal"),
                    _info_row("mdi:floor-plan", "Floors", "2 (Piso 0 + Piso 1)"),
                    _info_row("mdi:ruler-square", "Total Area", "\u2248 800 m\u00b2"),
                    _info_row("mdi:account-group", "Capacity", "454 occupants"),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "0",
                    "marginBottom": "16px",
                },
            ),
            html.P(
                "Aveiro is known for its lagoon, Art Nouveau architecture, "
                "and mild Atlantic climate.",
                style={
                    "fontSize": FONT_SIZE_SM,
                    "color": TEXT_TERTIARY,
                    "margin": 0,
                    "fontStyle": "italic",
                },
            ),
        ],
        style={
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "padding": f"{PADDING_CARD}px",
        },
    )

    return html.Div(
        [header, weather_card, map_card, building_card],
        className="page-enter",
    )


def _info_row(icon: str, label: str, value: str) -> html.Div:
    """Create a single label-value row for building information.

    Args:
        icon: Dash-iconify icon identifier.
        label: Row label text.
        value: Row value text.

    Returns:
        Dash html.Div containing the info row.
    """
    return html.Div(
        [
            html.Div(
                [
                    DashIconify(icon=icon, width=16, color=TEXT_SECONDARY),
                    html.Span(
                        label,
                        style={"fontSize": FONT_SIZE_SM, "color": TEXT_SECONDARY},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
            ),
            html.Span(
                value,
                style={
                    "fontSize": "14px",
                    "fontWeight": 500,
                    "fontFamily": FONT_DATA_STACK,
                },
            ),
        ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "padding": "8px 0",
            "borderBottom": "1px solid #F2F2F7",
        },
    )
