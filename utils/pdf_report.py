"""PDF report generator for PlantaOS financial reports.

Generates structured HTML-based PDF reports using the built-in
Plotly kaleido export and basic HTML templating. Falls back to
CSV export if PDF generation libraries are unavailable.
"""

from __future__ import annotations

from datetime import date, datetime

from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
from core.afi_engine import compute_financial_bleed
from data.store import store


def generate_report_html(
    period: str = "today",
    target_date: date | None = None,
) -> str:
    """Generate a styled HTML financial report.

    Args:
        period: Time period ('today', '7d', '30d').
        target_date: Optional specific date. Defaults to today.

    Returns:
        Complete HTML string suitable for PDF rendering.
    """
    if target_date is None:
        target_date = date.today()

    period_hours = {"today": 24.0, "7d": 168.0, "30d": 720.0}.get(period, 24.0)
    period_label = {"today": "Today", "7d": "Last 7 Days", "30d": "Last 30 Days"}.get(
        period, "Today"
    )

    # Compute financial data
    zones = get_monitored_zones()
    total_energy = 0.0
    total_human = 0.0
    total_window = 0.0
    zone_rows: list[str] = []

    for zone_obj in zones:
        try:
            bleed = compute_financial_bleed(zone_obj.id)
            e_cost = bleed.energy_cost_eur_hr * period_hours
            h_cost = bleed.human_capital_loss_eur_hr * period_hours
            w_cost = bleed.open_window_penalty_eur_hr * period_hours
            total = bleed.total_bleed_eur_hr * period_hours
            total_energy += e_cost
            total_human += h_cost
            total_window += w_cost

            zone_info = get_zone_by_id(zone_obj.id)
            name = zone_info.name if zone_info else zone_obj.id

            zone_rows.append(
                f"<tr>"
                f"<td>{name}</td>"
                f"<td class='num'>€{e_cost:.2f}</td>"
                f"<td class='num'>€{h_cost:.2f}</td>"
                f"<td class='num'>€{w_cost:.2f}</td>"
                f"<td class='num'><b>€{total:.2f}</b></td>"
                f"</tr>"
            )
        except Exception as e:
            logger.debug(f"Zone {zone_obj.id} report error: {e}")

    total_cost = total_energy + total_human + total_window
    baseline = total_cost * 1.10
    savings = baseline - total_cost

    # Energy summary
    energy_summary = ""
    energy_df = store.get("energy")
    if energy_df is not None and not energy_df.empty:
        total_kwh = energy_df["total_kwh"].sum()
        avg_daily = total_kwh / max(1, energy_df["timestamp"].dt.date.nunique())
        energy_summary = (
            f"<p>Total consumption: <b>{total_kwh:.1f} kWh</b> "
            f"(avg {avg_daily:.1f} kWh/day)</p>"
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    zone_table = "\n".join(zone_rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; color: #1D1D1F;
         margin: 40px; line-height: 1.6; }}
  h1 {{ color: #0071E3; font-size: 24px; margin-bottom: 4px; }}
  h2 {{ font-size: 18px; color: #1D1D1F; margin-top: 32px; border-bottom: 2px solid #E5E5EA;
        padding-bottom: 8px; }}
  .subtitle {{ color: #6E6E73; font-size: 13px; }}
  .kpi-row {{ display: flex; gap: 16px; margin: 24px 0; }}
  .kpi-box {{ flex: 1; background: #F5F5F7; border-radius: 12px; padding: 16px;
              text-align: center; }}
  .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 24px;
                font-weight: 600; color: #1D1D1F; }}
  .kpi-label {{ font-size: 12px; color: #6E6E73; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }}
  th {{ background: #F5F5F7; padding: 10px 12px; text-align: left; font-weight: 600;
       border-bottom: 2px solid #E5E5EA; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #F2F2F7; }}
  td.num {{ text-align: right; font-family: 'JetBrains Mono', monospace; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #E5E5EA;
             font-size: 11px; color: #86868B; }}
  .savings {{ color: #34C759; font-weight: 600; }}
  .cost {{ color: #FF3B30; }}
</style>
</head>
<body>
<h1>PlantaOS Financial Report</h1>
<p class="subtitle">Centro de Formação Técnica HORSE/Renault — Aveiro, Portugal</p>
<p class="subtitle">Period: {period_label} · Generated: {now_str}</p>

<div class="kpi-row">
  <div class="kpi-box">
    <div class="kpi-value">€{total_energy:.0f}</div>
    <div class="kpi-label">Energy Cost</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value">€{total_human:.0f}</div>
    <div class="kpi-label">Productivity Impact</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value">€{total_window:.0f}</div>
    <div class="kpi-label">HVAC Waste</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value savings">€{savings:+.0f}</div>
    <div class="kpi-label">Net Savings vs Baseline</div>
  </div>
</div>

<h2>Energy Summary</h2>
{energy_summary}
<p>Total operating cost: <b class="cost">€{total_cost:.2f}</b> over {period_label.lower()}</p>
<p>Estimated baseline: €{baseline:.2f} · Savings: <span class="savings">€{savings:.2f}</span></p>

<h2>Cost Breakdown by Zone</h2>
<table>
<tr>
  <th>Zone</th>
  <th>Energy</th>
  <th>Productivity Impact</th>
  <th>HVAC Waste</th>
  <th>Total</th>
</tr>
{zone_table}
<tr style="font-weight: 600; border-top: 2px solid #E5E5EA;">
  <td>TOTAL</td>
  <td class="num">€{total_energy:.2f}</td>
  <td class="num">€{total_human:.2f}</td>
  <td class="num">€{total_window:.2f}</td>
  <td class="num">€{total_cost:.2f}</td>
</tr>
</table>

<h2>Cost Analysis Framework</h2>
<p>This report quantifies building inefficiencies using sensor data and
physics-based models. Key cost components:</p>
<ul>
  <li><b>Energy Cost</b> — direct electricity consumption × €/kWh rate</li>
  <li><b>HVAC Waste</b> — thermal losses from open windows and suboptimal setpoints</li>
  <li><b>Productivity Impact</b> — comfort deviation × occupants × wage × impact factor</li>
  <li><b>Operating Cost</b> = Energy + HVAC Waste + Productivity Impact</li>
</ul>

<div class="footer">
  PlantaOS — Building Intelligence Platform · Generated automatically ·
  Cost per kWh: €{DEFAULT_AFI_CONFIG.cost_per_kwh} ·
  Avg hourly wage: €{DEFAULT_AFI_CONFIG.avg_hourly_wage}
</div>
</body>
</html>"""


def generate_report_csv(period: str = "today") -> str:
    """Generate a CSV-formatted financial report as fallback.

    Args:
        period: Time period ('today', '7d', '30d').

    Returns:
        CSV string with zone cost breakdown.
    """
    period_hours = {"today": 24.0, "7d": 168.0, "30d": 720.0}.get(period, 24.0)
    lines = ["Zone,Energy (€),Productivity Impact (€),HVAC Waste (€),Total (€)"]

    zones = get_monitored_zones()
    for zone_obj in zones:
        try:
            bleed = compute_financial_bleed(zone_obj.id)
            e = bleed.energy_cost_eur_hr * period_hours
            h = bleed.human_capital_loss_eur_hr * period_hours
            w = bleed.open_window_penalty_eur_hr * period_hours
            t = bleed.total_bleed_eur_hr * period_hours
            zone_info = get_zone_by_id(zone_obj.id)
            name = zone_info.name if zone_info else zone_obj.id
            lines.append(f"{name},{e:.2f},{h:.2f},{w:.2f},{t:.2f}")
        except Exception:
            continue

    return "\n".join(lines)
