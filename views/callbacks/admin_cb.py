"""Admin settings page callbacks.

Registers callbacks for saving configuration settings (energy cost,
hourly wage, API key), triggering synthetic data regeneration,
displaying system health status, audit log, and role settings.
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
    _register_audit_log(app)
    _register_role_settings(app)
    _register_integrity_panel(app)
    _register_login(app)
    _register_logout(app)
    _register_password_reset(app)


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

        from config.theme import TEXT_SECONDARY
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


def _register_audit_log(app: object) -> None:
    """Render audit log viewer and handle clear action."""

    @app.callback(
        Output("admin-audit-log-viewer", "children"),
        Input("audit-log-store", "data"),
        State("url", "pathname"),
    )
    @safe_callback
    def render_audit_log(
        audit_data: list | None,
        pathname: str | None,
    ) -> html.Div:
        """Render the last 20 audit log entries as a table.

        Args:
            audit_data: List of audit log entry dicts.
            pathname: Current page URL path.

        Returns:
            Dash component with audit log table or empty message.
        """
        if pathname != "/admin":
            return no_update

        if not audit_data:
            return html.Span(
                "No audit entries yet. Actions like sensor changes, "
                "tenant switches, and exports are logged here.",
                style={
                    "color": "#86868B",
                    "fontSize": "13px",
                },
            )

        # Show last 20 entries, newest first
        entries = list(audit_data[-20:])
        entries.reverse()

        header = html.Thead(
            html.Tr(
                [
                    html.Th(
                        col,
                        style={
                            "textAlign": "left",
                            "padding": "8px 12px",
                            "fontSize": "12px",
                            "fontWeight": 600,
                            "color": "#86868B",
                            "borderBottom": "1px solid #E5E5EA",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.5px",
                        },
                    )
                    for col in ["Timestamp", "Action", "User", "Details"]
                ]
            )
        )

        rows = []
        for entry in entries:
            rows.append(
                html.Tr(
                    [
                        html.Td(
                            entry.get("timestamp", "")[:19],
                            style={
                                "padding": "8px 12px",
                                "fontSize": "13px",
                                "color": "#6E6E73",
                                "fontFamily": "JetBrains Mono",
                            },
                        ),
                        html.Td(
                            entry.get("action", ""),
                            style={
                                "padding": "8px 12px",
                                "fontSize": "13px",
                                "fontWeight": 500,
                                "color": "#1D1D1F",
                            },
                        ),
                        html.Td(
                            entry.get("user", "Admin"),
                            style={
                                "padding": "8px 12px",
                                "fontSize": "13px",
                                "color": "#6E6E73",
                            },
                        ),
                        html.Td(
                            entry.get("details", ""),
                            style={
                                "padding": "8px 12px",
                                "fontSize": "13px",
                                "color": "#6E6E73",
                            },
                        ),
                    ],
                    style={"borderBottom": "1px solid #F2F2F7"},
                )
            )

        body = html.Tbody(rows)
        return html.Table(
            [header, body],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
            },
        )

    @app.callback(
        Output("admin-confirm-clear-audit", "displayed"),
        Input("admin-clear-audit-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    @safe_callback
    def show_clear_audit_confirm(n_clicks: int | None) -> bool:
        """Open confirmation dialog before clearing audit log."""
        return bool(n_clicks)

    @app.callback(
        Output("audit-log-store", "data", allow_duplicate=True),
        Input("admin-confirm-clear-audit", "submit_n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def clear_audit_log(
        n_clicks: int | None,
        pathname: str | None,
    ) -> list:
        """Clear all audit log entries.

        Args:
            n_clicks: Confirm dialog submit click count.
            pathname: Current URL path.

        Returns:
            Empty list to clear the audit store.
        """
        if n_clicks is None:
            raise PreventUpdate
        if pathname != "/admin":
            return no_update
        logger.info("Audit log cleared from admin page")
        return []


def _register_role_settings(app: object) -> None:
    """Persist role-related settings (require password toggle, camera)."""

    @app.callback(
        Output("admin-settings-store", "data", allow_duplicate=True),
        Input("admin-require-password", "value"),
        Input("admin-camera-toggle", "value"),
        State("admin-settings-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def save_role_settings(
        password_val: list | None,
        camera_val: list | None,
        current_settings: dict | None,
        pathname: str | None,
    ) -> dict:
        """Persist toggle states to admin-settings-store.

        Args:
            password_val: Checklist value for require-password toggle.
            camera_val: Checklist value for camera toggle.
            current_settings: Current stored settings dict.
            pathname: Current URL path.

        Returns:
            Updated settings dict.
        """
        if pathname != "/admin":
            return no_update

        settings_data = current_settings or {}
        settings_data["require_password"] = "require_password" in (password_val or [])
        settings_data["camera_enabled"] = "enabled" in (camera_val or [])
        logger.info(
            f"Role settings updated: password={settings_data['require_password']}, "
            f"camera={settings_data['camera_enabled']}"
        )
        return settings_data


def _register_integrity_panel(app: object) -> None:
    """Populate Architecture & Integrity card with runtime stack info."""

    @app.callback(
        Output("admin-integrity-content", "children"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    @safe_callback
    def update_integrity_panel(
        _n: int,
        pathname: str | None,
    ) -> html.Div:
        """Render runtime stack and dependency information.

        Args:
            _n: Interval tick count.
            pathname: Current page URL path.

        Returns:
            Dash html.Div with integrity data.
        """
        if pathname != "/admin":
            return no_update

        import importlib.metadata
        import platform
        from pathlib import Path

        from views.components.kpi_card import create_kpi_card

        # Python version
        py_version = platform.python_version()
        py_platform = platform.platform()

        # Dash version
        try:
            dash_version = importlib.metadata.version("dash")
        except importlib.metadata.PackageNotFoundError:
            dash_version = "unknown"

        # Package count
        pkg_count = len(list(importlib.metadata.distributions()))

        # Module count (local .py files)
        project_root = Path(__file__).resolve().parent.parent.parent
        module_count = 0
        for py_file in project_root.rglob("*.py"):
            rel_parts = py_file.relative_to(project_root).parts
            if any(
                p.startswith(".")
                or p == "__pycache__"
                or p in ("venv", ".venv", "node_modules")
                for p in rel_parts
            ):
                continue
            module_count += 1

        kpi_row = html.Div(
            [
                create_kpi_card(
                    "Python",
                    py_version,
                    icon="mdi:language-python",
                ),
                create_kpi_card(
                    "Dash",
                    dash_version,
                    icon="mdi:view-dashboard-outline",
                ),
                create_kpi_card(
                    "Packages",
                    str(pkg_count),
                    icon="mdi:package-variant-closed",
                ),
                create_kpi_card(
                    "Modules",
                    str(module_count),
                    icon="mdi:file-code-outline",
                ),
            ],
            className="grid-4",
        )

        detail_rows = [
            html.Div(
                [
                    html.Span(
                        label,
                        style={
                            "fontWeight": 500,
                            "fontSize": "13px",
                            "color": "#1D1D1F",
                            "minWidth": "140px",
                        },
                    ),
                    html.Span(
                        value,
                        style={
                            "fontSize": "13px",
                            "color": "#6E6E73",
                            "fontFamily": "JetBrains Mono",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "16px",
                    "padding": "6px 0",
                    "borderBottom": "1px solid #F2F2F7",
                },
            )
            for label, value in [
                ("Platform", py_platform),
                ("Implementation", platform.python_implementation()),
                ("Architecture", platform.machine()),
            ]
        ]

        return html.Div(
            [
                kpi_row,
                html.Div(
                    detail_rows,
                    style={
                        "marginTop": "16px",
                        "borderTop": "1px solid #E5E5EA",
                        "paddingTop": "12px",
                    },
                ),
            ]
        )


def _register_login(app: object) -> None:
    """Handle login button click — authenticate and store session."""

    @app.callback(
        Output("auth-store", "data", allow_duplicate=True),
        Output("admin-login-feedback", "children"),
        Input("admin-login-btn", "n_clicks"),
        State("admin-login-username", "value"),
        State("admin-login-password", "value"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def handle_login(
        n_clicks: int | None,
        username: str | None,
        password: str | None,
        pathname: str | None,
    ) -> tuple:
        """Authenticate user and persist session data.

        Args:
            n_clicks: Login button click count.
            username: Entered username.
            password: Entered password.
            pathname: Current URL path.

        Returns:
            Tuple of (auth data dict, feedback message).
        """
        if not n_clicks:
            raise PreventUpdate
        if pathname != "/admin":
            return no_update, no_update

        if not username or not password:
            return no_update, html.Span(
                "Please enter username and password",
                style={
                    "fontSize": "13px",
                    "color": "#FF9500",
                },
            )

        from config.auth import authenticate

        user = authenticate(username, password)
        if user is None:
            logger.warning(f"Failed login attempt for: {username}")
            return no_update, html.Span(
                "Invalid credentials",
                style={
                    "fontSize": "13px",
                    "color": "#FF3B30",
                },
            )

        logger.info(f"User logged in: {username}")
        auth_data = {
            "username": user.username,
            "role": user.role.value,
            "display_name": user.display_name,
        }
        return auth_data, html.Span(
            f"Logged in as {user.display_name} ({user.role.value})",
            style={
                "fontSize": "13px",
                "color": "#34C759",
            },
        )


def _register_logout(app: object) -> None:
    """Handle logout button click — clear session."""

    @app.callback(
        Output("auth-store", "data", allow_duplicate=True),
        Output("admin-auth-status", "children"),
        Input("admin-logout-btn", "n_clicks"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def handle_logout(
        n_clicks: int | None,
        pathname: str | None,
    ) -> tuple:
        """Clear auth session data.

        Args:
            n_clicks: Logout button click count.
            pathname: Current URL path.

        Returns:
            Tuple of (empty auth dict, status message).
        """
        if not n_clicks:
            raise PreventUpdate
        if pathname != "/admin":
            return no_update, no_update

        logger.info("User logged out")
        return {}, html.Span(
            "Not logged in",
            style={
                "fontSize": "13px",
                "color": "#86868B",
            },
        )


def _register_password_reset(app: object) -> None:
    """Handle password reset from admin panel."""

    @app.callback(
        Output("admin-reset-feedback", "children"),
        Input("admin-reset-password-btn", "n_clicks"),
        State("admin-reset-username", "value"),
        State("admin-reset-new-password", "value"),
        State("auth-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    @safe_callback
    def handle_password_reset(
        n_clicks: int | None,
        username: str | None,
        new_password: str | None,
        auth_data: dict | None,
        pathname: str | None,
    ) -> html.Span:
        """Reset a user password (admin only).

        Args:
            n_clicks: Reset button click count.
            username: Target username for reset.
            new_password: New password to set.
            auth_data: Current auth session data.
            pathname: Current URL path.

        Returns:
            Feedback message span.
        """
        if not n_clicks:
            raise PreventUpdate
        if pathname != "/admin":
            return no_update

        from config.auth import (
            UserRole,
            check_role,
            create_reset_token,
            validate_reset_token,
        )

        if not check_role(auth_data, UserRole.ADMIN):
            return html.Span(
                "Admin login required for password reset",
                style={
                    "fontSize": "13px",
                    "color": "#FF3B30",
                },
            )

        if not username or not new_password:
            return html.Span(
                "Please enter username and new password",
                style={
                    "fontSize": "13px",
                    "color": "#FF9500",
                },
            )

        token = create_reset_token(username)
        if token is None:
            return html.Span(
                f"User '{username}' not found",
                style={
                    "fontSize": "13px",
                    "color": "#FF3B30",
                },
            )

        success = validate_reset_token(token, new_password)
        if success:
            logger.info(f"Password reset for user: {username}")
            return html.Span(
                f"Password updated for {username}",
                style={
                    "fontSize": "13px",
                    "color": "#34C759",
                },
            )

        return html.Span(
            "Password reset failed",
            style={
                "fontSize": "13px",
                "color": "#FF3B30",
            },
        )
