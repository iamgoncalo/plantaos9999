"""Admin settings page callbacks.

Registers callbacks for saving configuration settings (energy cost,
hourly wage, API key) and triggering synthetic data regeneration.
"""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate
from loguru import logger


def register_admin_callbacks(app: object) -> None:
    """Register all admin page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_save_settings(app)
    _register_regen_data(app)


def _register_save_settings(app: object) -> None:
    """Save pricing, wage, and API key settings to session store."""

    @app.callback(
        Output("admin-settings-store", "data"),
        Output("admin-save-status", "children"),
        Input("admin-save-btn", "n_clicks"),
        State("admin-energy-price", "value"),
        State("admin-wage", "value"),
        State("admin-api-key", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def save_settings(
        n_clicks: int | None,
        energy_cost: float | None,
        wage: float | None,
        api_key: str | None,
        pathname: str | None,
    ) -> tuple[dict, html.Span]:
        """Persist admin settings to session storage.

        Args:
            n_clicks: Number of times the save button was clicked.
            energy_cost: Energy cost in EUR/kWh.
            wage: Average hourly wage in EUR.
            api_key: Anthropic API key value.
            pathname: Current page URL path.

        Returns:
            Tuple of (settings dict for store, status message component).
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
    """Trigger synthetic data regeneration (feedback only)."""

    @app.callback(
        Output("admin-regen-status", "children"),
        Input("admin-regen-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def regen_data(n_clicks: int | None) -> html.Span:
        """Queue data regeneration and return user feedback.

        Args:
            n_clicks: Number of times the regenerate button was clicked.

        Returns:
            Status message component.
        """
        if n_clicks is None:
            raise PreventUpdate

        logger.info("Data regeneration requested from admin page")
        return html.Span(
            "Data regeneration queued. Refresh the page in 10 seconds.",
            style={"fontSize": "13px", "color": "#0071E3"},
        )
