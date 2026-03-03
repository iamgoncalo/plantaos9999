"""Smart Booking page callbacks — orchestrator and booking actions.

Registers sub-module callbacks for room finding, calendar/analysis,
and handles the tab toggle and create/cancel booking flows.
"""

from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, html, no_update
from datetime import date, datetime
from loguru import logger

from config.building import get_zone_by_id
from config.theme import STATUS_CRITICAL, STATUS_HEALTHY
from views.components.safe_callback import safe_callback


def register_booking_callbacks(app: object) -> None:
    """Register all Smart Booking page callbacks."""
    from views.callbacks.booking_finder_cb import register_booking_finder_callbacks
    from views.callbacks.booking_calendar_cb import register_booking_calendar_callbacks

    register_booking_finder_callbacks(app)
    register_booking_calendar_callbacks(app)
    _register_tab_toggle(app)
    _register_book_room(app)
    _register_confirm_booking(app)
    _register_cancel_trigger(app)
    _register_confirm_cancel(app)


def _register_tab_toggle(app: object) -> None:
    """Clientside callback to toggle Find/Analyze sections."""
    app.clientside_callback(
        """
        function(tab) {
            var f = document.getElementById('booking-find-section');
            var a = document.getElementById('booking-analyze-section');
            if (f && a) {
                f.style.display = tab === 'find' ? 'flex' : 'none';
                a.style.display = tab === 'find' ? 'none' : 'flex';
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("booking-status-msg", "data-tab", allow_duplicate=True),
        Input("booking-tab", "value"),
        prevent_initial_call=True,
    )


def _register_book_room(app: object) -> None:
    """Show create-confirm dialog when Book button is clicked."""

    @app.callback(
        Output("booking-confirm-zone-store", "data"),
        Output("booking-create-confirm", "displayed"),
        Output("booking-create-confirm", "message"),
        Input({"type": "book-room-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_book(n_clicks_list: list) -> tuple:
        """Store zone ID and open create-confirm dialog."""
        if not any(n_clicks_list):
            return no_update, no_update, no_update
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update, no_update, no_update
        zone_id = triggered_id.get("index", "")
        zone = get_zone_by_id(zone_id)
        name = zone.name if zone else zone_id
        return zone_id, True, f"Create booking for {name}?"


def _register_confirm_booking(app: object) -> None:
    """Confirm booking creation and persist to bookings store."""

    @app.callback(
        Output("bookings-store", "data"),
        Output("booking-status-msg", "children"),
        Input("booking-create-confirm", "submit_n_clicks"),
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
        n_clicks,
        zone_id,
        selected_date,
        start_hour,
        duration,
        people,
        bookings,
        pathname,
    ) -> tuple:
        """Add confirmed booking to the bookings store."""
        if pathname != "/booking" or not n_clicks or not zone_id:
            return no_update, no_update
        bookings = list(bookings) if bookings else []
        duration, people = duration or 1, people or 15
        start_hour = start_hour or 9
        try:
            bdate = (
                datetime.fromisoformat(str(selected_date)).date()
                if selected_date
                else date.today()
            )
        except (ValueError, TypeError):
            bdate = date.today()
        zone = get_zone_by_id(zone_id)
        name = zone.name if zone else zone_id
        bookings.append(
            {
                "zone_id": zone_id,
                "zone_name": name,
                "date": str(bdate),
                "start_hour": start_hour,
                "duration": duration,
                "people": people,
            }
        )
        logger.info(f"Booking confirmed: {name} on {bdate} at {start_hour}:00")
        msg = (
            f"Booked {name} for {bdate} at "
            f"{start_hour:02d}:00 ({duration}h, {people} people)"
        )
        status = html.Div(
            html.Span(msg, style={"fontSize": "13px", "color": STATUS_HEALTHY}),
            style={"padding": "8px 0"},
        )
        return bookings, status


def _register_cancel_trigger(app: object) -> None:
    """Show cancel-confirm dialog when cancel button is clicked."""

    @app.callback(
        Output("booking-cancel-index-store", "data"),
        Output("booking-cancel-confirm", "displayed"),
        Input({"type": "cancel-booking-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_cancel(n_clicks_list: list) -> tuple:
        """Store booking index and open cancel dialog."""
        if not any(n or 0 for n in n_clicks_list):
            return no_update, no_update
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update, no_update
        return triggered_id.get("index", -1), True


def _register_confirm_cancel(app: object) -> None:
    """Confirm booking cancellation and remove from store."""

    @app.callback(
        Output("bookings-store", "data", allow_duplicate=True),
        Output("booking-status-msg", "children", allow_duplicate=True),
        Input("booking-cancel-confirm", "submit_n_clicks"),
        State("booking-cancel-index-store", "data"),
        State("bookings-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def confirm_cancel(n_clicks, booking_index, bookings, pathname) -> tuple:
        """Remove cancelled booking from the store."""
        if pathname != "/booking" or not n_clicks:
            return no_update, no_update
        if booking_index is None or booking_index < 0:
            return no_update, no_update
        bookings = list(bookings) if bookings else []
        if booking_index >= len(bookings):
            return no_update, no_update
        removed = bookings.pop(booking_index)
        name = removed.get("zone_name", removed.get("zone_id", "Room"))
        logger.info(f"Booking cancelled: {name}")
        status = html.Div(
            html.Span(
                f"Cancelled booking for {name}",
                style={"fontSize": "13px", "color": STATUS_CRITICAL},
            ),
            style={"padding": "8px 0"},
        )
        return bookings, status
