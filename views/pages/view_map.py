"""Map Overlay page — OpenStreetMap embed for CFT building context."""

from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    GAP_ELEMENT,
    PADDING_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

CFT_LAT = 40.6405
CFT_LON = -8.6538


def create_map_overlay_page() -> html.Div:
    """Create the Map Overlay page with OpenStreetMap embed."""
    bbox = (
        f"{CFT_LON - 0.004}%2C{CFT_LAT - 0.002}%2C{CFT_LON + 0.004}%2C{CFT_LAT + 0.002}"
    )
    osm_url = (
        f"https://www.openstreetmap.org/export/embed.html"
        f"?bbox={bbox}&layer=mapnik&marker={CFT_LAT}%2C{CFT_LON}"
    )

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
                        "Map Overlay",
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
                        "CFT HORSE/Renault — Aveiro, Portugal",
                        style={"fontSize": "13px", "color": TEXT_SECONDARY},
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

    map_card = html.Div(
        html.Iframe(
            src=osm_url,
            style={
                "width": "100%",
                "height": "520px",
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
        },
    )

    return html.Div(
        [header, map_card],
        className="page-enter",
    )
