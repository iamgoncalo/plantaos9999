"""Booking room-finder callback.

Ranks rooms by comfort, energy, and capacity fit for a booking request.
"""

from __future__ import annotations

from datetime import date, datetime

from dash import Input, Output, State, html, no_update

from config.building import get_monitored_zones
from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    CARD_RADIUS,
    CARD_SHADOW,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)
from utils.booking_helpers import (
    compute_requirement_bonus,
    compute_room_metrics,
    has_booking_conflict,
    score_room,
)
from views.components.safe_callback import safe_callback


def register_booking_finder_callbacks(app: object) -> None:
    """Register room finder callbacks."""
    _register_room_finder(app)


def _register_room_finder(app: object) -> None:
    """Rank and display available rooms based on user requirements."""

    @app.callback(
        Output("booking-results-container", "children"),
        Input("booking-find-btn", "n_clicks"),
        State("booking-date-picker", "date"),
        State("booking-time-start", "value"),
        State("booking-duration", "value"),
        State("booking-people", "value"),
        State("booking-floor-pref", "value"),
        State("booking-requirements", "value"),
        State("bookings-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def find_rooms(
        n_clicks,
        selected_date,
        start_hour,
        duration,
        people,
        floor_pref,
        requirements,
        bookings,
        pathname,
    ) -> list:
        """Find and rank available rooms for the requested slot."""
        if pathname != "/booking" or not n_clicks:
            return no_update
        duration, people = duration or 1, people or 15
        start_hour = start_hour or 9
        requirements, bookings = requirements or [], bookings or []
        try:
            bdate = (
                datetime.fromisoformat(str(selected_date)).date()
                if selected_date
                else date.today()
            )
        except (ValueError, TypeError):
            bdate = date.today()

        candidates = []
        for zone in get_monitored_zones():
            if zone.capacity <= 0 or zone.capacity < people:
                continue
            if floor_pref and floor_pref != "any":
                if zone.floor != int(floor_pref):
                    continue
            if has_booking_conflict(zone.id, bdate, start_hour, duration, bookings):
                continue
            primary = score_room(
                zone.id,
                zone.capacity,
                zone.zone_type.value,
                people,
                "projector" in requirements,
                "computers" in requirements,
                "quiet" in requirements,
            )
            metrics = compute_room_metrics(
                zone.area_m2, zone.capacity, people, duration
            )
            bonus = compute_requirement_bonus(zone.id, zone.capacity, requirements)
            metrics["total"] = min(100, round(primary + bonus, 1))
            candidates.append((metrics["total"], zone, metrics))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if not candidates:
            return [_no_rooms_message()]
        return [
            _build_room_card(z, s, i == 0)
            for i, (_t, z, s) in enumerate(candidates[:8])
        ]


def _no_rooms_message() -> html.Div:
    """Return empty-state message when no rooms match."""
    return html.Div(
        [
            html.P(
                "No rooms available for your requirements.",
                style={
                    "color": TEXT_SECONDARY,
                    "fontSize": "14px",
                    "textAlign": "center",
                    "padding": "32px",
                },
            ),
            html.P(
                "Try adjusting the number of people, date, or floor preference.",
                style={
                    "color": TEXT_TERTIARY,
                    "fontSize": "13px",
                    "textAlign": "center",
                },
            ),
        ]
    )


def _build_room_card(zone: object, scores: dict, is_best: bool) -> html.Div:
    """Build a styled room result card."""
    floor_label = "Piso 0" if zone.floor == 0 else "Piso 1"
    total = scores["total"]
    badge_color = (
        STATUS_HEALTHY
        if total >= 70
        else STATUS_WARNING
        if total >= 50
        else STATUS_CRITICAL
    )
    reasons = []
    if scores["comfort_score"] >= 80:
        reasons.append("excellent comfort conditions")
    elif scores["comfort_score"] >= 60:
        reasons.append("good comfort conditions")
    if scores["energy_cost"] < 0.5:
        reasons.append("low energy cost")
    if scores["capacity_fit"] >= 80:
        reasons.append("ideal capacity match")
    reason_text = (
        f"Best match: {', '.join(reasons)}." if reasons else f"Score {total:.0f}/100."
    )
    border = f"2px solid {ACCENT_BLUE}" if is_best else "1px solid #E5E5EA"
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                zone.name,
                                style={
                                    "fontSize": "15px",
                                    "fontWeight": 600,
                                    "color": TEXT_PRIMARY,
                                },
                            ),
                            html.Span(floor_label, className="status-badge"),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "flex": "1",
                        },
                    ),
                    html.Span(
                        f"{total:.0f}",
                        style={
                            "fontSize": "20px",
                            "fontWeight": 600,
                            "color": badge_color,
                            "fontFamily": "'JetBrains Mono', monospace",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                },
            ),
            html.Div(
                [
                    html.Span(
                        f"Capacity: {zone.capacity}",
                        style={"fontSize": "12px", "color": TEXT_SECONDARY},
                    ),
                    html.Span("|", style={"color": "#E5E5EA"}),
                    html.Span(
                        f"Comfort: {scores['comfort_score']:.0f}/100",
                        style={"fontSize": "12px", "color": TEXT_SECONDARY},
                    ),
                    html.Span("|", style={"color": "#E5E5EA"}),
                    html.Span(
                        f"Energy: ~{scores['energy_cost']:.2f} \u20ac",
                        style={"fontSize": "12px", "color": TEXT_SECONDARY},
                    ),
                    html.Span("|", style={"color": "#E5E5EA"}),
                    html.Span(
                        f"{zone.area_m2:.0f} m\u00b2",
                        style={"fontSize": "12px", "color": TEXT_SECONDARY},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "8px",
                    "flexWrap": "wrap",
                    "alignItems": "center",
                    "marginTop": "8px",
                },
            ),
            html.Div(
                [
                    html.Span(
                        reason_text,
                        style={"fontSize": "12px", "color": TEXT_TERTIARY, "flex": "1"},
                    ),
                    html.Button(
                        "Book",
                        id={"type": "book-room-btn", "index": zone.id},
                        n_clicks=0,
                        style={
                            "padding": "6px 20px",
                            "background": ACCENT_BLUE,
                            "color": "#FFFFFF",
                            "border": "none",
                            "borderRadius": "8px",
                            "fontSize": "13px",
                            "fontWeight": 600,
                            "cursor": "pointer",
                            "transition": "all 200ms ease",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "marginTop": "10px",
                },
            ),
        ],
        className="card",
        style={
            "padding": "16px 20px",
            "background": BG_CARD,
            "borderRadius": CARD_RADIUS,
            "boxShadow": CARD_SHADOW,
            "border": border,
        },
    )
