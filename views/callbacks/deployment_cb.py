"""Deployment page callbacks.

Registers callbacks for real-time AFI formula tuning and impact preview.
Slider changes are aggregated into an AFIConfig stored in dcc.Store,
then a second callback computes before/after Freedom and financial bleed
comparisons using the AFI engine.
"""

from __future__ import annotations

from dash import Input, Output, State, html, no_update
from dash_iconify import DashIconify
from loguru import logger

from config.afi_config import AFIConfig, DEFAULT_AFI_CONFIG
from core.afi_engine import compute_building_afi
from views.components.kpi_card import create_kpi_card


def register_deployment_callbacks(app: object) -> None:
    """Register all deployment page callbacks.

    Args:
        app: The Dash application instance.
    """
    _register_config_update(app)
    _register_impact_preview(app)
    _register_roi_calculator(app)


def _register_config_update(app: object) -> None:
    """Aggregate slider values into a serialized AFIConfig in the store."""

    @app.callback(
        Output("deploy-afi-config-store", "data"),
        Input("deploy-cost-slider", "value"),
        Input("deploy-wage-slider", "value"),
        Input("deploy-w-temp", "value"),
        Input("deploy-w-co2", "value"),
        Input("deploy-w-crowd", "value"),
        Input("deploy-w-exit", "value"),
        State("url", "pathname"),
    )
    def update_config_store(
        cost_kwh: float,
        wage: float,
        w_temp: float,
        w_co2: float,
        w_crowd: float,
        w_exit: float,
        pathname: str | None,
    ) -> dict | None:
        """Build a new AFIConfig from slider values and store it.

        Args:
            cost_kwh: Energy cost slider value.
            wage: Average hourly wage slider value.
            w_temp: Temperature weight slider value.
            w_co2: CO2 weight slider value.
            w_crowd: Crowding weight slider value.
            w_exit: Blocked exit weight slider value.
            pathname: Current page URL path.

        Returns:
            Serialized AFIConfig dict or no_update.
        """
        if pathname != "/deployment":
            return no_update

        try:
            config = AFIConfig(
                cost_per_kwh=cost_kwh,
                avg_hourly_wage=wage,
                w_temperature=w_temp,
                w_co2=w_co2,
                w_crowding=w_crowd,
                w_blocked_exit=w_exit,
            )
            return config.model_dump()
        except Exception as exc:
            logger.warning(f"Deployment config store error: {exc}")
            return no_update


def _register_impact_preview(app: object) -> None:
    """Compute before/after AFI comparison when config store changes."""

    @app.callback(
        Output("deploy-impact-preview", "children"),
        Input("deploy-afi-config-store", "data"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_impact_preview(
        config_data: dict | None,
        n_intervals: int | None,
        pathname: str | None,
    ) -> html.Div:
        """Render before/after Freedom and bleed comparison.

        Args:
            config_data: Serialized AFIConfig from the store.
            n_intervals: Data refresh interval tick count.
            pathname: Current page URL path.

        Returns:
            Dash html.Div with KPI cards showing current vs modified metrics.
        """
        if pathname != "/deployment":
            return no_update

        if not config_data:
            return html.Div(
                "Adjust parameters to preview the impact on "
                "Freedom and financial bleed.",
                style={"fontSize": "13px", "color": "#6E6E73"},
            )

        try:
            modified_cfg = AFIConfig(**config_data)

            # Compute building-wide AFI with default and modified configs
            default_afi = compute_building_afi(config=DEFAULT_AFI_CONFIG)
            modified_afi = compute_building_afi(config=modified_cfg)

            # Extract key metrics
            current_freedom = default_afi.avg_freedom
            modified_freedom = modified_afi.avg_freedom
            delta_freedom = modified_freedom - current_freedom

            current_bleed = default_afi.total_financial_bleed_eur_hr
            modified_bleed = modified_afi.total_financial_bleed_eur_hr
            delta_bleed = modified_bleed - current_bleed

            # Compute trend percentages for KPI cards
            freedom_trend = (
                (delta_freedom / current_freedom * 100) if current_freedom > 0 else 0.0
            )
            bleed_trend = (
                -(delta_bleed / current_bleed * 100) if current_bleed > 0 else 0.0
            )

            # Build comparison layout with KPI cards
            return html.Div(
                [
                    # Section: Current vs Modified Freedom
                    html.Div(
                        [
                            html.Div(
                                "Health Comparison",
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": 600,
                                    "marginBottom": "12px",
                                },
                            ),
                            html.Div(
                                [
                                    create_kpi_card(
                                        title="Current Health",
                                        value=f"{current_freedom:.3f}",
                                        icon="mdi:shield-check-outline",
                                    ),
                                    create_kpi_card(
                                        title="Modified Health",
                                        value=f"{modified_freedom:.3f}",
                                        trend=freedom_trend,
                                        icon="mdi:shield-edit-outline",
                                    ),
                                    create_kpi_card(
                                        title="\u0394Health",
                                        value=f"{delta_freedom:+.4f}",
                                        icon="mdi:delta",
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "12px",
                                    "flexWrap": "wrap",
                                },
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    # Section: Current vs Modified Bleed
                    html.Div(
                        [
                            html.Div(
                                "Operating Cost Comparison",
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": 600,
                                    "marginBottom": "12px",
                                },
                            ),
                            html.Div(
                                [
                                    create_kpi_card(
                                        title="Current Cost",
                                        value=f"\u20ac{current_bleed:.4f}",
                                        unit="/hr",
                                        icon="mdi:cash-minus",
                                    ),
                                    create_kpi_card(
                                        title="Modified Cost",
                                        value=f"\u20ac{modified_bleed:.4f}",
                                        unit="/hr",
                                        trend=bleed_trend,
                                        icon="mdi:cash-check",
                                    ),
                                    create_kpi_card(
                                        title="\u0394Cost",
                                        value=f"\u20ac{delta_bleed:+.4f}",
                                        unit="/hr",
                                        icon="mdi:delta",
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "12px",
                                    "flexWrap": "wrap",
                                },
                            ),
                        ],
                    ),
                ],
            )

        except Exception as exc:
            logger.warning(f"Deployment impact preview error: {exc}")
            return html.Div(
                [
                    DashIconify(
                        icon="mdi:alert-circle-outline",
                        width=18,
                        color="#FF3B30",
                    ),
                    html.Span(
                        f"Error computing impact preview: {exc}",
                        style={"fontSize": "13px", "color": "#FF3B30"},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
            )


def _register_roi_calculator(app: object) -> None:
    """Register the ROI calculator callback.

    Computes total hardware cost, estimated monthly savings, payback
    period, and annual ROI from sensor deployment inputs.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("deploy-roi-summary", "children"),
        Input("deploy-sensor-count", "value"),
        Input("deploy-sensor-cost", "value"),
        Input("deploy-install-cost", "value"),
        Input("data-refresh-interval", "n_intervals"),
        State("url", "pathname"),
    )
    def update_roi(
        sensor_count: int | None,
        sensor_cost: float | None,
        install_cost: float | None,
        _n: int,
        pathname: str | None,
    ) -> html.Div:
        """Compute and display ROI metrics.

        Args:
            sensor_count: Number of sensors to deploy.
            sensor_cost: Cost per sensor in EUR.
            install_cost: One-time installation cost in EUR.
            _n: Interval tick (triggers refresh).
            pathname: Current URL pathname.

        Returns:
            Dash html.Div with ROI KPI cards.
        """
        if pathname != "/deployment":
            return no_update

        try:
            n_sensors = int(sensor_count or 16)
            cost_each = float(sensor_cost or 150)
            install = float(install_cost or 2000)

            total_hardware = n_sensors * cost_each + install

            # Estimate monthly savings from current building bleed
            try:
                afi = compute_building_afi()
                current_bleed = afi.total_financial_bleed_eur_hr
            except Exception:
                current_bleed = 3.0  # fallback estimate

            # Assume sensors reduce bleed by 30-50% depending on count
            reduction_pct = min(0.5, 0.02 * n_sensors)
            monthly_savings = current_bleed * reduction_pct * 720

            # Payback and ROI
            if monthly_savings > 0:
                payback_months = total_hardware / monthly_savings
                annual_roi = (
                    (monthly_savings * 12 - total_hardware) / total_hardware
                ) * 100
            else:
                payback_months = float("inf")
                annual_roi = 0.0

            payback_str = f"{payback_months:.0f}" if payback_months < 100 else "N/A"

            return html.Div(
                [
                    create_kpi_card(
                        title="Hardware Investment",
                        value=f"€{total_hardware:,.0f}",
                        icon="mdi:chip",
                    ),
                    create_kpi_card(
                        title="Monthly Savings",
                        value=f"€{monthly_savings:.0f}",
                        icon="mdi:piggy-bank-outline",
                    ),
                    create_kpi_card(
                        title="Payback Period",
                        value=payback_str,
                        unit="months",
                        icon="mdi:calendar-clock",
                    ),
                    create_kpi_card(
                        title="Annual ROI",
                        value=f"{annual_roi:+.0f}%",
                        icon="mdi:trending-up",
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                },
            )
        except Exception as exc:
            logger.warning(f"ROI calculator error: {exc}")
            return html.Span(
                "Error calculating ROI.",
                style={"color": "#FF3B30", "fontSize": "13px"},
            )
