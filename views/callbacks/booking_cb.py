"""Smart Booking page callbacks — orchestrator and booking actions.

Registers sub-module callbacks for room finding, calendar/analysis,
and handles the tab toggle and create/cancel booking flows with
confirmation modals.
"""

from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, html, no_update
from datetime import date, datetime
from loguru import logger

from config.building import get_zone_by_id
from config.theme import (
    STATUS_HEALTHY,
    STATUS_CRITICAL,
)
from views.components.safe_callback import safe_callback


def register_booking_callbacks(app: object) -> None:
    """Register all Smart Booking page callbacks.

    Imports and delegates to sub-modules for room finding and
    calendar/analysis, then registers local booking action callbacks.

    Args:
        app: The Dash application instance.
    """
    from views.callbacks.booking_finder_cb import (
        register_booking_finder_callbacks,
    )
    from views.callbacks.booking_calendar_cb import (
        register_booking_calendar_callbacks,
    )

    register_booking_finder_callbacks(app)
    register_booking_calendar_callbacks(app)
    _register_tab_toggle(app)
    _register_book_room(app)
    _register_confirm_booking(app)
    _register_cancel_trigger(app)
    _register_confirm_cancel(app)


# ===================================================
# Tab Toggle
# ===================================================


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


# ===================================================
# Book Room — trigger create-confirm dialog
# ===================================================


def _register_book_room(app: object) -> None:
    """Show create-confirm dialog when a room's Book button is clicked."""

    @app.callback(
        Output("booking-confirm-zone-store", "data"),
        Output("booking-create-confirm", "displayed"),
        Output("booking-create-confirm", "message"),
        Input({"type": "book-room-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_book(n_clicks_list: list) -> tuple:
        """Store the triggered zone ID and open create-confirm dialog.

        Args:
            n_clicks_list: List of click counts for all Book buttons.

        Returns:
            Tuple of (zone_id, display_flag, message).
        """
        if not any(n_clicks_list):
            return no_update, no_update, no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update, no_update, no_update

        zone_id = triggered_id.get("index", "")
        zone = get_zone_by_id(zone_id)
        zone_name = zone.name if zone else zone_id

        return (
            zone_id,
            True,
            f"Create this booking for {zone_name}? "
            f"The room will be reserved for the specified time.",
        )


# ===================================================
# Confirm Create Booking
# ===================================================


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
            return no_update, no_update

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


# ===================================================
# Cancel Booking — trigger cancel-confirm dialog
# ===================================================


def _register_cancel_trigger(app: object) -> None:
    """Show cancel-confirm dialog when a cancel button is clicked."""

    @app.callback(
        Output("booking-cancel-index-store", "data"),
        Output("booking-cancel-confirm", "displayed"),
        Input({"type": "cancel-booking-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def trigger_cancel(n_clicks_list: list) -> tuple:
        """Store the triggered booking index and open cancel dialog.

        Args:
            n_clicks_list: List of click counts for cancel buttons.

        Returns:
            Tuple of (booking_index, display_flag).
        """
        if not any(n or 0 for n in n_clicks_list):
            return no_update, no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update, no_update

        booking_index = triggered_id.get("index", -1)
        return booking_index, True


# ===================================================
# Confirm Cancel Booking
# ===================================================


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
    def confirm_cancel(
        n_clicks: int | None,
        booking_index: int | None,
        bookings: list | None,
        pathname: str | None,
    ) -> tuple:
        """Remove cancelled booking from the store.

        Args:
            n_clicks: Confirm dialog submit click count.
            booking_index: Index of the booking to cancel.
            bookings: Current bookings list.
            pathname: Current page URL.

        Returns:
            Tuple of (updated bookings list, status message).
        """
        if pathname != "/booking" or not n_clicks:
            return no_update, no_update
        if booking_index is None or booking_index < 0:
            return no_update, no_update

        bookings = list(bookings) if bookings else []
        if booking_index >= len(bookings):
            return no_update, no_update

        removed = bookings.pop(booking_index)
        zone_name = removed.get("zone_name", removed.get("zone_id", "Room"))

        logger.info(f"Booking cancelled: {zone_name}")

        status = html.Div(
            html.Span(
                f"Cancelled booking for {zone_name}",
                style={"fontSize": "13px", "color": STATUS_CRITICAL},
            ),
            style={"padding": "8px 0"},
        )

        return bookings, status
