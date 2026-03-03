"""Smart Booking page callbacks.

Registers callbacks for:
- Tab switching between Find Room and Analyze Room
- Room finder: ranks rooms by comfort, energy, and capacity fit
- Booking confirmation: stores bookings in memory
- Calendar view: today's bookings as a timeline
- Room analysis: historical look-back and future projections
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from datetime import date, datetime, timedelta
from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
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
from data.store import store
from views.charts import apply_chart_theme, empty_chart
from views.components.kpi_card import create_kpi_card
from views.components.safe_callback import safe_callback

try:
    from data.physical_ai_bridge import (
        RoomPhysicsState,
        simulate_room_physics,
    )

    HAS_PHYSICS = True
except ImportError:
    HAS_PHYSICS = False


def register_booking_callbacks(app: object) -> None:
    """Register all Smart Booking page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_tab_toggle(app)
    _register_room_finder(app)
    _register_book_room(app)
    _register_confirm_booking(app)
    _register_calendar_view(app)
    _register_booking_analysis(app)


# ═══════════════════════════════════════════════
# Tab Toggle
# ═══════════════════════════════════════════════


def _register_tab_toggle(app: object) -> None:
    """Clientside callback to toggle Find/Analyze sections."""
    app.clientside_callback(
        """
        function(tab) {
            var findEl = document.getElementById('booking-find-section');
            var analyzeEl = document.getElementById('booking-analyze-section');
            if (findEl && analyzeEl) {
                if (tab === 'find') {
                    findEl.style.display = 'flex';
                    analyzeEl.style.display = 'none';
                } else {
                    findEl.style.display = 'none';
                    analyzeEl.style.display = 'flex';
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("booking-status-msg", "data-tab", allow_duplicate=True),
        Input("booking-tab", "value"),
        prevent_initial_call=True,
    )


# ═══════════════════════════════════════════════
# Room Finder
# ═══════════════════════════════════════════════


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
        State("bookings-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def find_rooms(
        n_clicks: int | None,
        selected_date: str | None,
        start_hour: int | None,
        duration: int | None,
        people: int | None,
        floor_pref: str | None,
        bookings: list | None,
        pathname: str | None,
    ) -> list:
        """Find and rank available rooms for the requested slot.

        Args:
            n_clicks: Find button click count.
            selected_date: Selected date string.
            start_hour: Start hour (6-22).
            duration: Duration in hours.
            people: Number of occupants.
            floor_pref: Floor preference ("any", "0", "1").
            bookings: Current bookings list from store.
            pathname: Current page URL.

        Returns:
            List of room card components ranked by suitability.
        """
        if pathname != "/booking":
            raise PreventUpdate
        if not n_clicks:
            raise PreventUpdate

        duration = duration or 1
        people = people or 15
        start_hour = start_hour or 9
        bookings = bookings or []

        # Parse date
        try:
            booking_date = (
                datetime.fromisoformat(str(selected_date)).date()
                if selected_date
                else date.today()
            )
        except (ValueError, TypeError):
            booking_date = date.today()

        # Get candidate zones
        candidates = []
        for zone in get_monitored_zones():
            if zone.capacity <= 0 or zone.capacity < people:
                continue
            if floor_pref and floor_pref != "any":
                if zone.floor != int(floor_pref):
                    continue

            # Check for booking conflicts
            if _has_conflict(zone.id, booking_date, start_hour, duration, bookings):
                continue

            # Score the room
            score_data = _score_room(zone, people, duration)
            candidates.append((score_data["total"], zone, score_data))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if not candidates:
            return [
                html.Div(
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
                            "Try adjusting the number of people, date, "
                            "or floor preference.",
                            style={
                                "color": TEXT_TERTIARY,
                                "fontSize": "13px",
                                "textAlign": "center",
                            },
                        ),
                    ]
                )
            ]

        cards = []
        for rank, (total, zone, scores) in enumerate(candidates[:8]):
            cards.append(_build_room_card(zone, scores, rank == 0))

        return cards

    return find_rooms


def _has_conflict(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    bookings: list,
) -> bool:
    """Check if a booking conflicts with existing bookings.

    Args:
        zone_id: Zone identifier.
        booking_date: Date of the proposed booking.
        start_hour: Start hour.
        duration: Duration in hours.
        bookings: Existing bookings list.

    Returns:
        True if there is a conflict.
    """
    date_str = str(booking_date)
    new_start = start_hour
    new_end = start_hour + duration

    for b in bookings:
        if b.get("zone_id") != zone_id:
            continue
        if b.get("date") != date_str:
            continue
        b_start = b.get("start_hour", 0)
        b_end = b_start + b.get("duration", 0)
        if new_start < b_end and new_end > b_start:
            return True

    return False


def _score_room(
    zone: object,
    people: int,
    duration: int,
) -> dict:
    """Score a room on comfort, energy, and capacity fit.

    Args:
        zone: Zone model object.
        people: Requested occupant count.
        duration: Duration in hours.

    Returns:
        Dict with comfort_score, energy_score, capacity_fit, total, etc.
    """
    area = zone.area_m2
    capacity = zone.capacity

    # Comfort prediction via fallback model
    steps = duration * 4
    temps, co2s = _fallback_projection(people, area, duration, steps)
    avg_temp = sum(temps) / len(temps) if temps else 22.0
    avg_co2 = sum(co2s) / len(co2s) if co2s else 500.0

    temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    comfort_score = (temp_score + co2_score) / 2.0

    # Energy prediction
    hvac_load_kw = (
        DEFAULT_AFI_CONFIG.air_density
        * DEFAULT_AFI_CONFIG.air_specific_heat
        * area
        * DEFAULT_AFI_CONFIG.ceiling_height_m
        * temp_dev
        / (3600 * DEFAULT_AFI_CONFIG.hvac_efficiency)
    )
    energy_kwh = max(0.5, hvac_load_kw * duration + people * 0.05 * duration)
    energy_cost = energy_kwh * DEFAULT_AFI_CONFIG.cost_per_kwh
    # Normalize: 0 = expensive (~5 EUR), 100 = cheap (~0 EUR)
    energy_score = max(0.0, 100.0 - energy_cost * 20.0)

    # Capacity fit: 1.0 when people == capacity, lower when mismatch
    capacity_fit = 1.0 - abs(capacity - people) / capacity
    capacity_fit_score = capacity_fit * 100.0

    total = 0.45 * comfort_score + 0.35 * energy_score + 0.20 * capacity_fit_score

    return {
        "comfort_score": round(comfort_score, 1),
        "energy_score": round(energy_score, 1),
        "energy_kwh": round(energy_kwh, 1),
        "energy_cost": round(energy_cost, 2),
        "capacity_fit": round(capacity_fit_score, 1),
        "total": round(total, 1),
        "avg_temp": round(avg_temp, 1),
        "peak_co2": round(max(co2s) if co2s else 500, 0),
    }


def _build_room_card(
    zone: object,
    scores: dict,
    is_best: bool,
) -> html.Div:
    """Build a styled room result card.

    Args:
        zone: Zone model object.
        scores: Score dict from _score_room().
        is_best: Whether this is the top-ranked room.

    Returns:
        Dash html.Div with room details and Book button.
    """
    floor_label = "Piso 0" if zone.floor == 0 else "Piso 1"
    badge_color = (
        STATUS_HEALTHY
        if scores["total"] >= 70
        else (STATUS_WARNING if scores["total"] >= 50 else STATUS_CRITICAL)
    )

    # Reason text
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
        f"Best match: {', '.join(reasons)}."
        if reasons
        else f"Score {scores['total']:.0f}/100."
    )

    border_style = f"2px solid {ACCENT_BLUE}" if is_best else "1px solid #E5E5EA"

    return html.Div(
        [
            # Top row: name + floor badge + score
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
                            html.Span(
                                floor_label,
                                style={
                                    "fontSize": "11px",
                                    "fontWeight": 500,
                                    "color": "#FFFFFF",
                                    "background": "#86868B",
                                    "borderRadius": "4px",
                                    "padding": "2px 8px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "flex": "1",
                        },
                    ),
                    html.Span(
                        f"{scores['total']:.0f}",
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
            # Metrics row
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
            # Reason + Book button
            html.Div(
                [
                    html.Span(
                        reason_text,
                        style={
                            "fontSize": "12px",
                            "color": TEXT_TERTIARY,
                            "flex": "1",
                        },
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
            "border": border_style,
        },
    )


# ═══════════════════════════════════════════════
# Book Room + Confirm
# ═══════════════════════════════════════════════


def _register_book_room(app: object) -> None:
    """Show confirmation dialog when a room's Book button is clicked."""

    @app.callback(
        Output("booking-confirm-zone-store", "data"),
        Output("booking-confirm-dialog", "displayed"),
        Output("booking-confirm-dialog", "message"),
        Input({"type": "book-room-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_book(n_clicks_list: list) -> tuple:
        """Store the triggered zone ID and open confirm dialog.

        Args:
            n_clicks_list: List of click counts for all Book buttons.

        Returns:
            Tuple of (zone_id, display_flag, message).
        """
        if not any(n_clicks_list):
            raise PreventUpdate

        triggered_id = ctx.triggered_id
        if not triggered_id:
            raise PreventUpdate

        zone_id = triggered_id.get("index", "")
        zone = get_zone_by_id(zone_id)
        zone_name = zone.name if zone else zone_id

        return (
            zone_id,
            True,
            f"Book {zone_name}?",
        )


def _register_confirm_booking(app: object) -> None:
    """Confirm booking and persist to bookings store."""

    @app.callback(
        Output("bookings-store", "data"),
        Output("booking-status-msg", "children"),
        Input("booking-confirm-dialog", "submit_n_clicks"),
        State("booking-confirm-zone-store", "data"),
        State("booking-date-picker", "date"),
        State("booking-time-start", "value"),
        State("booking-duration", "value"),
        State("booking-people", "value"),
        State("bookings-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def confirm_booking(
        n_clicks: int | None,
        zone_id: str | None,
        selected_date: str | None,
        start_hour: int | None,
        duration: int | None,
        people: int | None,
        bookings: list | None,
        pathname: str | None,
    ) -> tuple:
        """Add confirmed booking to the bookings store.

        Args:
            n_clicks: Confirm dialog submit click count.
            zone_id: Selected zone ID from the store.
            selected_date: Booking date string.
            start_hour: Start hour.
            duration: Duration in hours.
            people: Number of occupants.
            bookings: Current bookings list.
            pathname: Current page URL.

        Returns:
            Tuple of (updated bookings list, status message).
        """
        if pathname != "/booking" or not n_clicks or not zone_id:
            raise PreventUpdate

        bookings = list(bookings) if bookings else []
        duration = duration or 1
        people = people or 15
        start_hour = start_hour or 9

        try:
            booking_date = (
                datetime.fromisoformat(str(selected_date)).date()
                if selected_date
                else date.today()
            )
        except (ValueError, TypeError):
            booking_date = date.today()

        zone = get_zone_by_id(zone_id)
        zone_name = zone.name if zone else zone_id

        new_booking = {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "date": str(booking_date),
            "start_hour": start_hour,
            "duration": duration,
            "people": people,
        }
        bookings.append(new_booking)

        logger.info(
            f"Booking confirmed: {zone_name} on {booking_date} "
            f"at {start_hour}:00 for {duration}h, {people} people"
        )

        status = html.Div(
            html.Span(
                f"Booked {zone_name} for {booking_date} at "
                f"{start_hour:02d}:00 ({duration}h, {people} people)",
                style={"fontSize": "13px", "color": STATUS_HEALTHY},
            ),
            style={"padding": "8px 0"},
        )

        return bookings, status


# ═══════════════════════════════════════════════
# Calendar View
# ═══════════════════════════════════════════════


def _register_calendar_view(app: object) -> None:
    """Render today's bookings as a timeline chart."""

    @app.callback(
        Output("booking-calendar-chart", "figure"),
        Input("bookings-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_calendar(
        bookings: list | None,
        pathname: str | None,
    ) -> go.Figure:
        """Build a timeline chart of today's bookings.

        Args:
            bookings: Current bookings list from store.
            pathname: Current page URL.

        Returns:
            Plotly Figure with booking timeline bars.
        """
        if pathname != "/booking":
            raise PreventUpdate

        bookings = bookings or []
        today_str = str(date.today())
        today_bookings = [b for b in bookings if b.get("date") == today_str]

        if not today_bookings:
            return _empty_calendar()

        fig = go.Figure()
        colors = [
            ACCENT_BLUE,
            STATUS_HEALTHY,
            STATUS_WARNING,
            "#5AC8FA",
            "#AF52DE",
            "#FF2D55",
        ]

        for i, b in enumerate(today_bookings):
            zone_name = b.get("zone_name", b.get("zone_id", "Room"))
            start_h = b.get("start_hour", 9)
            dur = b.get("duration", 1)
            people = b.get("people", 0)

            fig.add_trace(
                go.Bar(
                    x=[dur],
                    y=[zone_name],
                    base=[start_h],
                    orientation="h",
                    marker=dict(
                        color=colors[i % len(colors)],
                        cornerradius=4,
                    ),
                    text=f"{start_h:02d}:00-{start_h + dur:02d}:00 ({people}p)",
                    textposition="inside",
                    textfont=dict(size=11, color="#FFFFFF"),
                    hovertemplate=(
                        f"<b>{zone_name}</b><br>"
                        f"{start_h:02d}:00 - {start_h + dur:02d}:00<br>"
                        f"{people} people<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

        fig.update_layout(
            xaxis=dict(
                title="Hour",
                range=[6, 22],
                dtick=2,
                tickvals=list(range(6, 23, 2)),
                ticktext=[f"{h:02d}:00" for h in range(6, 23, 2)],
            ),
            yaxis=dict(title=""),
            barmode="overlay",
            height=180,
        )

        return apply_chart_theme(fig, "", height=180)

    return update_calendar


def _empty_calendar() -> go.Figure:
    """Return an empty calendar chart with placeholder message."""
    fig = go.Figure()
    fig.add_annotation(
        text="No bookings for today. Find a room above.",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color=TEXT_TERTIARY),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=180,
    )
    return apply_chart_theme(fig, "", height=180)


# ═══════════════════════════════════════════════
# Room Analysis (Analyze Tab — existing logic)
# ═══════════════════════════════════════════════


def _register_booking_analysis(app: object) -> None:
    """Register the room analysis callback (Look Back / Look Forward)."""

    @app.callback(
        Output("booking-kpi-grid", "children"),
        Output("booking-physics-chart", "figure"),
        Output("booking-recommendation", "children"),
        Input("booking-analyze-btn", "n_clicks"),
        State("booking-mode", "value"),
        State("booking-zone-selector", "value"),
        State("booking-date-picker", "date"),
        State("booking-time-start", "value"),
        State("booking-duration", "value"),
        State("booking-people", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def analyze_booking(
        n_clicks: int | None,
        mode: str | None,
        zone_id: str | None,
        selected_date: str | None,
        start_hour: int | None,
        duration: int | None,
        people: int | None,
        pathname: str | None,
    ) -> tuple[list, go.Figure, html.Div]:
        """Run booking analysis for the selected parameters.

        Args:
            n_clicks: Analyze button click count.
            mode: "past" for Look Back, "future" for Look Forward.
            zone_id: Selected zone identifier.
            selected_date: Date string from the date picker.
            start_hour: Start hour (6-22).
            duration: Duration in hours (1, 2, 4, 8).
            people: Number of occupants.
            pathname: Current page URL path.

        Returns:
            Tuple of (KPI card list, physics chart figure,
            recommendation div).
        """
        if pathname != "/booking":
            raise PreventUpdate
        if not n_clicks:
            raise PreventUpdate
        if not zone_id or not selected_date or start_hour is None:
            raise PreventUpdate

        duration = duration or 1
        people = people or 15

        try:
            booking_date = datetime.fromisoformat(str(selected_date)).date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid booking date: {selected_date}")
            raise PreventUpdate

        try:
            if mode == "future":
                return _analyze_forward(
                    zone_id, booking_date, start_hour, duration, people
                )
            else:
                return _analyze_backward(
                    zone_id, booking_date, start_hour, duration, people
                )
        except PreventUpdate:
            raise
        except Exception as exc:
            logger.warning(f"Booking analysis error: {exc}")
            return no_update, no_update, no_update


# ═══════════════════════════════════════════════
# Look Back: Historical Analysis
# ═══════════════════════════════════════════════


def _analyze_backward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Analyze a past booking window using historical data.

    Args:
        zone_id: Zone identifier.
        booking_date: The date of the past booking.
        start_hour: Start hour of the booking window.
        duration: Duration in hours.
        people: Number of occupants.

    Returns:
        Tuple of (KPI cards, physics chart, recommendation).
    """
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id

    start_dt = datetime.combine(
        booking_date, datetime.min.time().replace(hour=start_hour)
    )
    end_dt = start_dt + timedelta(hours=duration)

    # Fetch historical data
    energy_df = store.get_time_range("energy", start_dt, end_dt)
    comfort_df = store.get_time_range("comfort", start_dt, end_dt)

    # NaN defense
    for df in [energy_df, comfort_df]:
        if df is not None and not df.empty:
            for col in df.select_dtypes(include=["number"]).columns:
                df[col] = df[col].ffill().bfill().fillna(0)

    # Filter to zone
    if energy_df is not None and not energy_df.empty and "zone_id" in energy_df.columns:
        energy_df = energy_df[energy_df["zone_id"] == zone_id]
    if (
        comfort_df is not None
        and not comfort_df.empty
        and "zone_id" in comfort_df.columns
    ):
        comfort_df = comfort_df[comfort_df["zone_id"] == zone_id]

    # Energy KPI
    energy_kwh = 0.0
    if (
        energy_df is not None
        and not energy_df.empty
        and "total_kwh" in energy_df.columns
    ):
        energy_kwh = float(energy_df["total_kwh"].sum())

    # Comfort index
    comfort_index = 50.0
    avg_temp = None
    avg_co2 = None

    if comfort_df is not None and not comfort_df.empty:
        scores = []
        if "temperature_c" in comfort_df.columns:
            avg_temp = float(comfort_df["temperature_c"].mean())
            temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
            scores.append(max(0.0, 100.0 - temp_dev * 15.0))
        if "co2_ppm" in comfort_df.columns:
            avg_co2 = float(comfort_df["co2_ppm"].mean())
            co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
            scores.append(max(0.0, 100.0 - co2_dev * 0.1))
        if scores:
            comfort_index = sum(scores) / len(scores)

    performance = comfort_index * 0.85 + 15.0
    avg_wage = DEFAULT_AFI_CONFIG.avg_hourly_wage
    added_value = (performance / 100.0) * avg_wage * duration * people

    # Build KPIs
    kpis = [
        create_kpi_card(
            "Energy Used", f"{energy_kwh:.1f}", unit="kWh", icon="mdi:flash"
        ),
        create_kpi_card(
            "Comfort Index",
            f"{comfort_index:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card(
            "Added Value", f"{added_value:.0f}", unit="\u20ac", icon="mdi:currency-eur"
        ),
        create_kpi_card(
            "Zone Performance",
            f"{performance:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    # Chart
    fig = _build_historical_chart(comfort_df, start_dt, end_dt, zone_name)

    # Recommendation
    if comfort_index >= 75:
        status_color, status_text = STATUS_HEALTHY, "Excellent"
        rec_text = (
            f"Historical analysis for {zone_name}: comfort conditions were "
            f"excellent during this {duration}h window."
        )
        if avg_temp is not None and avg_co2 is not None:
            rec_text += (
                f" Average temperature {avg_temp:.1f} \u00b0C, "
                f"CO\u2082 {avg_co2:.0f} ppm. "
                f"Estimated added value: \u20ac{added_value:.0f} for {people} people."
            )
    elif comfort_index >= 50:
        status_color, status_text = STATUS_WARNING, "Moderate"
        rec_text = (
            f"Historical analysis for {zone_name}: moderate comfort during "
            f"this {duration}h window. Consider reviewing HVAC schedules."
        )
    else:
        status_color, status_text = STATUS_CRITICAL, "Poor"
        rec_text = (
            f"Historical analysis for {zone_name}: poor comfort conditions. "
            f"Recommend choosing an alternative room or time."
        )

    recommendation = _build_recommendation(status_color, status_text, rec_text)
    return kpis, fig, recommendation


def _build_historical_chart(
    comfort_df: object,
    start_dt: datetime,
    end_dt: datetime,
    zone_name: str,
) -> go.Figure:
    """Build a dual-axis chart with historical temperature and CO2."""
    if comfort_df is None or comfort_df.empty:
        return empty_chart("No historical comfort data for this window")

    fig = go.Figure()

    if "temperature_c" in comfort_df.columns and "timestamp" in comfort_df.columns:
        fig.add_trace(
            go.Scatter(
                x=comfort_df["timestamp"],
                y=comfort_df["temperature_c"],
                mode="lines",
                name="Temperature (\u00b0C)",
                line=dict(color=STATUS_CRITICAL, width=2),
                hovertemplate="%{x|%H:%M}<br>%{y:.1f} \u00b0C<extra></extra>",
            )
        )

    if "co2_ppm" in comfort_df.columns and "timestamp" in comfort_df.columns:
        fig.add_trace(
            go.Scatter(
                x=comfort_df["timestamp"],
                y=comfort_df["co2_ppm"],
                mode="lines",
                name="CO\u2082 (ppm)",
                line=dict(color=STATUS_WARNING, width=2),
                yaxis="y2",
                hovertemplate="%{x|%H:%M}<br>%{y:.0f} ppm<extra></extra>",
            )
        )

    fig.update_layout(
        yaxis=dict(
            title="Temperature (\u00b0C)",
            titlefont=dict(color=STATUS_CRITICAL),
            tickfont=dict(color=STATUS_CRITICAL),
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            tickfont=dict(color=STATUS_WARNING),
            overlaying="y",
            side="right",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
        ),
    )

    return apply_chart_theme(fig, f"Historical Comfort \u2014 {zone_name}", height=360)


# ═══════════════════════════════════════════════
# Look Forward: Future Projection
# ═══════════════════════════════════════════════


def _analyze_forward(
    zone_id: str,
    booking_date: date,
    start_hour: int,
    duration: int,
    people: int,
) -> tuple[list, go.Figure, html.Div]:
    """Project future booking metrics using physics simulation."""
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    zone_area = zone.area_m2 if zone else 40.0
    zone_capacity = zone.capacity if zone else 30

    steps = duration * 4
    timestamps = [
        datetime.combine(
            booking_date,
            datetime.min.time().replace(hour=start_hour),
        )
        + timedelta(minutes=15 * i)
        for i in range(steps + 1)
    ]

    if HAS_PHYSICS:
        try:
            initial_state = RoomPhysicsState(
                zone_id=zone_id,
                temperature_c=DEFAULT_AFI_CONFIG.optimal_temperature_c,
                co2_ppm=DEFAULT_AFI_CONFIG.optimal_co2_ppm,
                humidity_pct=50.0,
                occupant_count=people,
                hvac_power_w=2000.0,
                ventilation_ach=2.0,
            )
            sim_result = simulate_room_physics(
                initial_state,
                area_m2=zone_area,
                duration_minutes=duration * 60,
                step_minutes=15,
            )
            temps = [s.temperature_c for s in sim_result]
            co2s = [s.co2_ppm for s in sim_result]
            temps = (temps + [temps[-1]] * len(timestamps))[: len(timestamps)]
            co2s = (co2s + [co2s[-1]] * len(timestamps))[: len(timestamps)]
        except Exception as exc:
            logger.warning(f"Physics simulation failed: {exc}")
            temps, co2s = _fallback_projection(people, zone_area, duration, steps)
    else:
        temps, co2s = _fallback_projection(people, zone_area, duration, steps)

    avg_temp = sum(temps) / len(temps)
    avg_co2 = sum(co2s) / len(co2s)
    peak_co2 = max(co2s)

    temp_dev = abs(avg_temp - DEFAULT_AFI_CONFIG.optimal_temperature_c)
    hvac_load_kw = (
        DEFAULT_AFI_CONFIG.air_density
        * DEFAULT_AFI_CONFIG.air_specific_heat
        * zone_area
        * DEFAULT_AFI_CONFIG.ceiling_height_m
        * temp_dev
        / (3600 * DEFAULT_AFI_CONFIG.hvac_efficiency)
    )
    projected_energy = max(0.5, hvac_load_kw * duration + people * 0.05 * duration)

    temp_score = max(0.0, 100.0 - temp_dev * 15.0)
    co2_dev = max(0.0, avg_co2 - DEFAULT_AFI_CONFIG.optimal_co2_ppm)
    co2_score = max(0.0, 100.0 - co2_dev * 0.1)
    predicted_comfort = (temp_score + co2_score) / 2.0

    projected_performance = predicted_comfort * 0.85 + 15.0

    optimal_room = _find_optimal_room(people)

    kpis = [
        create_kpi_card(
            "Projected Energy",
            f"{projected_energy:.1f}",
            unit="kWh",
            icon="mdi:flash-outline",
        ),
        create_kpi_card(
            "Predicted Comfort",
            f"{predicted_comfort:.0f}",
            unit="/100",
            icon="mdi:thermometer-check",
        ),
        create_kpi_card("Optimal Room", optimal_room, icon="mdi:star-outline"),
        create_kpi_card(
            "Zone Performance",
            f"{projected_performance:.0f}",
            unit="/100",
            icon="mdi:shield-check-outline",
        ),
    ]

    fig = _build_projection_chart(timestamps, temps, co2s, zone_name)

    occupancy_ratio = people / zone_capacity if zone_capacity > 0 else 1.0

    if predicted_comfort >= 75 and occupancy_ratio <= 0.85:
        status_color, status_text = STATUS_HEALTHY, "Recommended"
        rec_text = (
            f"{zone_name} is an excellent choice for {people} people over "
            f"{duration}h. Projected comfort {predicted_comfort:.0f}/100, "
            f"peak CO\u2082 {peak_co2:.0f} ppm, energy cost "
            f"\u20ac{projected_energy * DEFAULT_AFI_CONFIG.cost_per_kwh:.2f}."
        )
    elif predicted_comfort >= 50 or occupancy_ratio <= 1.0:
        status_color, status_text = STATUS_WARNING, "Acceptable"
        rec_text = (
            f"{zone_name} can accommodate {people} people but conditions "
            f"may degrade. Consider {optimal_room} for better comfort."
        )
    else:
        status_color, status_text = STATUS_CRITICAL, "Not Recommended"
        rec_text = (
            f"{zone_name} is not suitable for {people} people over "
            f"{duration}h. Strongly recommend {optimal_room} instead."
        )

    recommendation = _build_recommendation(status_color, status_text, rec_text)
    return kpis, fig, recommendation


# ═══════════════════════════════════════════════
# Shared Helpers
# ═══════════════════════════════════════════════


def _fallback_projection(
    people: int,
    area_m2: float,
    duration: int,
    steps: int,
) -> tuple[list[float], list[float]]:
    """Generate simplified temperature and CO2 projections.

    Args:
        people: Number of occupants.
        area_m2: Room area in square meters.
        duration: Booking duration in hours.
        steps: Number of 15-minute intervals.

    Returns:
        Tuple of (temperature list, CO2 list) with steps+1 entries.
    """
    base_temp = DEFAULT_AFI_CONFIG.optimal_temperature_c
    base_co2 = DEFAULT_AFI_CONFIG.optimal_co2_ppm

    heat_per_person_kw = 0.08
    co2_per_person_ppm_per_step = 5.0
    thermal_mass = area_m2 * DEFAULT_AFI_CONFIG.ceiling_height_m * 1.2
    ventilation_decay = 0.02

    temps = [base_temp]
    co2s = [base_co2]

    for _i in range(steps):
        heat_input = people * heat_per_person_kw * 0.25
        temp_rise = heat_input / thermal_mass * 100
        hvac_correction = (temps[-1] - base_temp) * 0.3
        new_temp = temps[-1] + temp_rise - hvac_correction
        temps.append(round(new_temp, 2))

        co2_input = people * co2_per_person_ppm_per_step
        co2_removal = (co2s[-1] - 400) * ventilation_decay
        new_co2 = co2s[-1] + co2_input - co2_removal
        co2s.append(round(max(400.0, new_co2), 1))

    return temps, co2s


def _build_projection_chart(
    timestamps: list[datetime],
    temps: list[float],
    co2s: list[float],
    zone_name: str,
) -> go.Figure:
    """Build a dual-axis chart with projected temperature and CO2."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=temps,
            mode="lines",
            name="Projected Temp (\u00b0C)",
            line=dict(color=STATUS_CRITICAL, width=2),
            hovertemplate="%{x|%H:%M}<br>%{y:.1f} \u00b0C<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=co2s,
            mode="lines",
            name="Projected CO\u2082 (ppm)",
            line=dict(color=STATUS_WARNING, width=2),
            yaxis="y2",
            hovertemplate="%{x|%H:%M}<br>%{y:.0f} ppm<extra></extra>",
        )
    )

    fig.update_layout(
        yaxis=dict(
            title="Temperature (\u00b0C)",
            titlefont=dict(color=STATUS_CRITICAL),
            tickfont=dict(color=STATUS_CRITICAL),
        ),
        yaxis2=dict(
            title="CO\u2082 (ppm)",
            titlefont=dict(color=STATUS_WARNING),
            tickfont=dict(color=STATUS_WARNING),
            overlaying="y",
            side="right",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
        ),
    )

    return apply_chart_theme(fig, f"Projected Comfort \u2014 {zone_name}", height=360)


def _find_optimal_room(people: int) -> str:
    """Find the best room for the given occupant count.

    Args:
        people: Expected number of occupants.

    Returns:
        Display name of the optimal zone.
    """
    candidates = []
    for zone in get_monitored_zones():
        if zone.capacity >= people:
            distortion = (zone.capacity - people) / zone.capacity
            candidates.append((distortion, zone))

    if not candidates:
        all_zones = get_monitored_zones()
        if all_zones:
            return max(all_zones, key=lambda z: z.capacity).name
        return "N/A"

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1].name


def _build_recommendation(
    status_color: str,
    status_text: str,
    rec_text: str,
) -> html.Div:
    """Build the recommendation card with status badge and text."""
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        style={
                            "width": "10px",
                            "height": "10px",
                            "borderRadius": "50%",
                            "background": status_color,
                            "display": "inline-block",
                            "flexShrink": 0,
                        },
                    ),
                    html.Span(
                        status_text,
                        style={
                            "fontWeight": 600,
                            "fontSize": "15px",
                            "color": TEXT_PRIMARY,
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "10px",
                    "marginBottom": "8px",
                },
            ),
            html.P(
                rec_text,
                style={
                    "margin": 0,
                    "color": TEXT_SECONDARY,
                    "fontSize": "13px",
                    "lineHeight": "1.5",
                },
            ),
        ],
        style={"padding": "16px 20px"},
    )
