"""Admin settings page callbacks.

Registers callbacks for saving configuration settings (energy cost,
hourly wage, API key), triggering synthetic data regeneration, and
displaying system health status.
"""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate
from loguru import logger

from views.components.safe_callback import safe_callback


def register_admin_callbacks(app: object) -> None:
    """Register all admin page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_save_settings(app)
    _register_regen_data(app)
    _register_clear_bookings(app)
    _register_system_health(app)


def _register_save_settings(app: object) -> None:
    """Save pricing, wage, and API key settings with confirmation."""

    @app.callback(
        Output("admin-confirm-save", "displayed"),
        Input("admin-save-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_save_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before saving settings."""
        return bool(n_clicks)

    @app.callback(
        Output("admin-settings-store", "data"),
        Output("admin-save-status", "children"),
        Input("admin-confirm-save", "submit_n_clicks"),
        State("admin-energy-price", "value"),
        State("admin-wage", "value"),
        State("admin-api-key", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def save_settings(
        n_clicks: int | None,
        energy_cost: float | None,
        wage: float | None,
        api_key: str | None,
        pathname: str | None,
    ) -> tuple[dict, html.Span]:
        """Persist admin settings to session storage.

        Args:
            n_clicks: Confirm dialog submit click count.
            energy_cost: Energy cost in EUR/kWh.
            wage: Average hourly wage in EUR.
            api_key: Anthropic API key value.
            pathname: Current page URL path.

        Returns:
            Tuple of (settings dict for store, status message).
        """
        if n_clicks is None:
            raise PreventUpdate

        if pathname != "/admin":
            return no_update, no_update

        try:
            settings = {
                "energy_cost": energy_cost,
                "wage": wage,
                "api_key": "***" if api_key else None,
            }
            logger.info(f"Admin settings saved: cost={energy_cost}, wage={wage}")
            return settings, html.Span(
                "Settings saved successfully",
                style={"fontSize": "13px", "color": "#34C759"},
            )
        except Exception as exc:
            logger.warning(f"Admin save settings error: {exc}")
            return no_update, html.Span(
                f"Error saving settings: {exc}",
                style={"fontSize": "13px", "color": "#FF3B30"},
            )


def _register_regen_data(app: object) -> None:
    """Trigger data regeneration with confirmation dialog."""

    @app.callback(
        Output("admin-confirm-regen", "displayed"),
        Input("admin-regen-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_regen_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before regenerating data."""
        return bool(n_clicks)

    @app.callback(
        Output("admin-regen-status", "children"),
        Input("admin-confirm-regen", "submit_n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def regen_data(n_clicks: int | None) -> html.Span:
        """Regenerate synthetic data and return user feedback.

        Args:
            n_clicks: Confirm dialog submit click count.

        Returns:
            Status message component.
        """
        if n_clicks is None:
            raise PreventUpdate

        try:
            from data.pipeline import run_pipeline

            logger.info("Data regeneration triggered from admin page")
            run_pipeline(days=30, seed=None)
            logger.info("Data regeneration complete")
            return html.Span(
                "Data regeneration complete. Dashboard is updating.",
                style={"fontSize": "13px", "color": "#34C759"},
            )
        except Exception as exc:
            logger.warning(f"Data regeneration error: {exc}")
            return html.Span(
                f"Regeneration failed: {exc}",
                style={"fontSize": "13px", "color": "#FF3B30"},
            )


def _register_clear_bookings(app: object) -> None:
    """Clear all bookings from the bookings store with confirmation."""

    @app.callback(
        Output("admin-confirm-clear-bookings", "displayed"),
        Input("admin-clear-bookings-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_clear_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before clearing bookings."""
        return bool(n_clicks)

    @app.callback(
        Output("bookings-store", "data", allow_duplicate=True),
        Output("admin-clear-bookings-status", "children"),
        Input("admin-confirm-clear-bookings", "submit_n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def clear_bookings(
        n_clicks: int | None,
        pathname: str | None,
    ) -> tuple:
        """Clear all bookings from store.

        Args:
            n_clicks: Confirm dialog submit click count.
            pathname: Current page URL path.

        Returns:
            Tuple of (empty bookings list, status message).
        """
        if n_clicks is None:
            raise PreventUpdate
        if pathname != "/admin":
            return no_update, no_update

        logger.info("All bookings cleared from admin page")
        return [], html.Span(
            "All bookings cleared.",
            style={"fontSize": "13px", "color": "#34C759"},
        )


def _register_system_health(app: object) -> None:
    """Show data pipeline status and store health."""

    @app.callback(
        Output("admin-system-health", "children"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_system_health(_n: int, pathname: str | None) -> html.Div:
        """Render system health dashboard with store metrics.

        Args:
            _n: Interval tick count.
            pathname: Current page URL path.

        Returns:
            Dash html.Div with system health indicators.
        """
        if pathname != "/admin":
            return no_update

        from config.theme import (
            TEXT_SECONDARY,
        )
        from data.store import store
        from views.components.kpi_card import create_kpi_card

        datasets = list(store.keys())
        total_rows = 0
        status_items = []
        for name in datasets:
            df = store.get(name)
            rows = len(df) if df is not None and not df.empty else 0
            total_rows += rows
            dot_class = "status-dot healthy" if rows > 0 else "status-dot warning"
            status_items.append(
                html.Div(
                    [
                        html.Span(className=dot_class),
                        html.Span(
                            f"{name}: {rows:,} rows",
                            style={
                                "fontSize": "13px",
                                "color": TEXT_SECONDARY,
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "padding": "6px 0",
                    },
                )
            )

        return html.Div(
            [
                html.Div(
                    [
                        create_kpi_card(
                            "Datasets",
                            str(len(datasets)),
                            icon="mdi:database-outline",
                        ),
                        create_kpi_card(
                            "Total Records",
                            f"{total_rows:,}",
                            icon="mdi:table-large",
                        ),
                        create_kpi_card(
                            "Store Version",
                            str(store.version),
                            icon="mdi:counter",
                        ),
                        create_kpi_card(
                            "Pipeline",
                            "Active",
                            icon="mdi:check-circle-outline",
                        ),
                    ],
                    className="grid-4",
                ),
                html.Div(
                    status_items,
                    style={
                        "borderTop": "1px solid #E5E5EA",
                        "paddingTop": "12px",
                        "marginTop": "12px",
                    },
                ),
            ]
        )
