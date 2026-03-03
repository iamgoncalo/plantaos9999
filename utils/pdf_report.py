"""PDF report generator for PlantaOS financial reports.

Generates structured reports in PDF (via reportlab), HTML, and CSV formats.
Charts are rendered as base64-embedded PNG images via kaleido for offline viewing.
Falls back to CSV export if generation fails.
"""

from __future__ import annotations

import base64
import io
from datetime import date, datetime
from typing import Any

import plotly.graph_objects as go
from loguru import logger

from config.afi_config import DEFAULT_AFI_CONFIG
from config.building import get_monitored_zones, get_zone_by_id
from core.afi_engine import compute_financial_bleed
from data.store import store


# ═══════════════════════════════════════════════
# Shared data helpers
# ═══════════════════════════════════════════════


def _get_report_data(
    period: str = "today",
    target_date: date | None = None,
) -> dict[str, Any]:
    """Compute financial data shared across all report formats.

    Args:
        period: Time period ('today', '7d', '30d').
        target_date: Optional specific date. Defaults to today.

    Returns:
        Dict with totals, zone_rows, energy summary, and metadata.
    """
    if target_date is None:
        target_date = date.today()

    period_hours = {"today": 24.0, "7d": 168.0, "30d": 720.0}.get(period, 24.0)
    period_label = {"today": "Today", "7d": "Last 7 Days", "30d": "Last 30 Days"}.get(
        period, "Today"
    )

    zones = get_monitored_zones()
    total_energy = 0.0
    total_human = 0.0
    total_window = 0.0
    zone_data: list[dict[str, Any]] = []

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

            zone_data.append(
                {
                    "name": name,
                    "energy_cost": e_cost,
                    "human_cost": h_cost,
                    "window_cost": w_cost,
                    "total_cost": total,
                }
            )
        except Exception as e:
            logger.debug(f"Zone {zone_obj.id} report error: {e}")

    total_cost = total_energy + total_human + total_window
    baseline = total_cost * 1.10
    savings = baseline - total_cost

    # Energy summary
    total_kwh = 0.0
    avg_daily_kwh = 0.0
    energy_df = store.get("energy")
    if energy_df is not None and not energy_df.empty:
        total_kwh = energy_df["total_kwh"].sum()
        avg_daily_kwh = total_kwh / max(1, energy_df["timestamp"].dt.date.nunique())

    return {
        "period": period,
        "period_label": period_label,
        "period_hours": period_hours,
        "target_date": target_date,
        "total_energy": total_energy,
        "total_human": total_human,
        "total_window": total_window,
        "total_cost": total_cost,
        "baseline": baseline,
        "savings": savings,
        "zone_data": zone_data,
        "total_kwh": total_kwh,
        "avg_daily_kwh": avg_daily_kwh,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ═══════════════════════════════════════════════
# Chart helpers (shared by HTML and PDF)
# ═══════════════════════════════════════════════


def _fig_to_base64(fig: go.Figure, width: int = 700, height: int = 350) -> str:
    """Render a Plotly figure to a base64-encoded PNG string.

    Args:
        fig: Plotly figure to render.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Base64 data URI string, or empty string on failure.
    """
    try:
        img_bytes = fig.to_image(
            format="png", width=width, height=height, engine="kaleido"
        )
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:
        logger.debug(f"Chart image render failed: {exc}")
        return ""


def _fig_to_png_bytes(fig: go.Figure, width: int = 500, height: int = 280) -> bytes:
    """Render a Plotly figure to PNG bytes for PDF embedding.

    Args:
        fig: Plotly figure to render.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        PNG bytes, or empty bytes on failure.
    """
    try:
        return fig.to_image(format="png", width=width, height=height, engine="kaleido")
    except Exception as exc:
        logger.debug(f"Chart PNG render failed: {exc}")
        return b""


def _build_breakdown_pie_fig(
    total_energy: float, total_human: float, total_window: float
) -> go.Figure | None:
    """Build cost breakdown pie chart figure.

    Args:
        total_energy: Total energy cost.
        total_human: Total productivity impact cost.
        total_window: Total HVAC waste cost.

    Returns:
        Plotly Figure or None if no data.
    """
    values = [total_energy, total_human, total_window]
    if sum(values) == 0:
        return None
    fig = go.Figure(
        go.Pie(
            labels=["Energy Cost", "Productivity Impact", "HVAC Waste"],
            values=values,
            marker=dict(colors=["#0071E3", "#FF9500", "#FF3B30"]),
            hole=0.45,
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        title="Cost Breakdown",
        paper_bgcolor="#FFFFFF",
    )
    return fig


def _build_zone_bar_fig(zone_data: list[dict]) -> go.Figure | None:
    """Build zone ranking bar chart figure.

    Args:
        zone_data: List of dicts with 'name' and 'total_cost' keys.

    Returns:
        Plotly Figure or None if no data.
    """
    if not zone_data:
        return None
    top10 = sorted(zone_data, key=lambda x: x["total_cost"], reverse=True)[:10]
    names = [z["name"] for z in reversed(top10)]
    costs = [z["total_cost"] for z in reversed(top10)]
    fig = go.Figure(
        go.Bar(x=costs, y=names, orientation="h", marker=dict(color="#0071E3"))
    )
    fig.update_layout(
        margin=dict(l=120, r=20, t=40, b=20),
        title="Cost by Zone (Top 10)",
        xaxis_title="Cost (\u20ac)",
        paper_bgcolor="#FFFFFF",
    )
    return fig


# ═══════════════════════════════════════════════
# PDF Report (reportlab)
# ═══════════════════════════════════════════════


def generate_report_pdf(
    period: str = "today", target_date: date | None = None
) -> bytes:
    """Generate a styled PDF financial report.

    Uses reportlab to produce a properly formatted A4 PDF with cover
    section, KPI summary table, zone breakdown, optional embedded charts,
    and page numbers.

    Args:
        period: Time period ('today', '7d', '30d').
        target_date: Optional specific date. Defaults to today.

    Returns:
        PDF content as bytes.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    data = _get_report_data(period, target_date)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
    )

    # ── Custom styles ──────────────────────────
    styles = getSampleStyleSheet()

    planta_blue = colors.HexColor("#0071E3")
    text_primary = colors.HexColor("#1D1D1F")
    text_secondary = colors.HexColor("#6E6E73")
    text_tertiary = colors.HexColor("#86868B")
    bg_light = colors.HexColor("#F5F5F7")
    border_color = colors.HexColor("#E5E5EA")
    green = colors.HexColor("#34C759")  # noqa: F841
    red = colors.HexColor("#FF3B30")  # noqa: F841
    white = colors.white

    style_title = ParagraphStyle(
        "PlantaTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=planta_blue,
        spaceAfter=4,
        leading=26,
    )
    style_subtitle = ParagraphStyle(
        "PlantaSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=text_secondary,
        spaceAfter=2,
        leading=14,
    )
    style_heading = ParagraphStyle(
        "PlantaHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=text_primary,
        spaceBefore=18,
        spaceAfter=8,
        leading=18,
        borderWidth=0,
        borderPadding=0,
    )
    style_body = ParagraphStyle(
        "PlantaBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=text_primary,
        leading=14,
    )
    style_body_right = ParagraphStyle(
        "PlantaBodyRight",
        parent=style_body,
        alignment=TA_RIGHT,
    )
    style_small = ParagraphStyle(
        "PlantaSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=text_tertiary,
        leading=10,
    )
    style_kpi_value = ParagraphStyle(
        "PlantaKPIValue",
        parent=styles["Normal"],
        fontSize=16,
        textColor=text_primary,
        alignment=TA_CENTER,
        leading=20,
        spaceBefore=4,
        spaceAfter=2,
    )
    style_kpi_label = ParagraphStyle(
        "PlantaKPILabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=text_secondary,
        alignment=TA_CENTER,
        leading=10,
    )

    elements: list = []

    # ── Cover section ──────────────────────────
    elements.append(Paragraph("PlantaOS Financial Report", style_title))
    elements.append(
        Paragraph(
            "Centro de Forma\u00e7\u00e3o T\u00e9cnica HORSE/Renault "
            "\u2014 Aveiro, Portugal",
            style_subtitle,
        )
    )
    elements.append(
        Paragraph(
            f"Period: {data['period_label']}  \u00b7  "
            f"Generated: {data['generated_at']}",
            style_subtitle,
        )
    )
    elements.append(Spacer(1, 16))

    # ── KPI summary table (4 columns) ─────────
    savings_color = "#34C759" if data["savings"] >= 0 else "#FF3B30"
    kpi_data = [
        [
            Paragraph(f"<b>\u20ac{data['total_energy']:.0f}</b>", style_kpi_value),
            Paragraph(f"<b>\u20ac{data['total_cost']:.0f}</b>", style_kpi_value),
            Paragraph(f"<b>{data['total_kwh']:.0f} kWh</b>", style_kpi_value),
            Paragraph(
                f"<b><font color='{savings_color}'>"
                f"\u20ac{data['savings']:+.0f}</font></b>",
                style_kpi_value,
            ),
        ],
        [
            Paragraph("Energy Cost", style_kpi_label),
            Paragraph("Operating Cost", style_kpi_label),
            Paragraph("Total Consumption", style_kpi_label),
            Paragraph("Net Savings vs Baseline", style_kpi_label),
        ],
    ]

    page_width = A4[0] - 40 * mm
    col_w = page_width / 4.0
    kpi_table = Table(kpi_data, colWidths=[col_w] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("LINEBELOW", (0, 0), (-1, 0), 0, white),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    # ── Energy summary ─────────────────────────
    elements.append(Paragraph("Energy Summary", style_heading))
    if data["total_kwh"] > 0:
        elements.append(
            Paragraph(
                f"Total consumption: <b>{data['total_kwh']:.1f} kWh</b> "
                f"(avg {data['avg_daily_kwh']:.1f} kWh/day)",
                style_body,
            )
        )
    elements.append(
        Paragraph(
            f"Total operating cost: <b><font color='#FF3B30'>"
            f"\u20ac{data['total_cost']:.2f}</font></b> "
            f"over {data['period_label'].lower()}",
            style_body,
        )
    )
    elements.append(
        Paragraph(
            f"Estimated baseline: \u20ac{data['baseline']:.2f}  \u00b7  "
            f"Savings: <font color='#34C759'>"
            f"\u20ac{data['savings']:.2f}</font>",
            style_body,
        )
    )
    elements.append(Spacer(1, 8))

    # ── Zone breakdown table ───────────────────
    elements.append(Paragraph("Cost Breakdown by Zone", style_heading))

    header = [
        Paragraph("<b>Zone</b>", style_body),
        Paragraph("<b>Energy</b>", style_body_right),
        Paragraph("<b>Productivity</b>", style_body_right),
        Paragraph("<b>HVAC Waste</b>", style_body_right),
        Paragraph("<b>Total</b>", style_body_right),
    ]
    table_data = [header]

    for zd in data["zone_data"]:
        table_data.append(
            [
                Paragraph(zd["name"], style_body),
                Paragraph(f"\u20ac{zd['energy_cost']:.2f}", style_body_right),
                Paragraph(f"\u20ac{zd['human_cost']:.2f}", style_body_right),
                Paragraph(f"\u20ac{zd['window_cost']:.2f}", style_body_right),
                Paragraph(f"<b>\u20ac{zd['total_cost']:.2f}</b>", style_body_right),
            ]
        )

    # Totals row
    table_data.append(
        [
            Paragraph("<b>TOTAL</b>", style_body),
            Paragraph(f"<b>\u20ac{data['total_energy']:.2f}</b>", style_body_right),
            Paragraph(f"<b>\u20ac{data['total_human']:.2f}</b>", style_body_right),
            Paragraph(f"<b>\u20ac{data['total_window']:.2f}</b>", style_body_right),
            Paragraph(f"<b>\u20ac{data['total_cost']:.2f}</b>", style_body_right),
        ]
    )

    zone_col_widths = [
        page_width * 0.32,
        page_width * 0.17,
        page_width * 0.17,
        page_width * 0.17,
        page_width * 0.17,
    ]
    zone_table = Table(table_data, colWidths=zone_col_widths, repeatRows=1)

    # Alternating row colors
    zone_style_cmds: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), bg_light),
        ("TEXTCOLOR", (0, 0), (-1, 0), text_primary),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, border_color),
        ("LINEBELOW", (0, -2), (-1, -2), 1.5, border_color),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, border_color),
    ]
    # Alternating row colors for data rows
    for i in range(1, len(table_data) - 1):
        if i % 2 == 0:
            zone_style_cmds.append(
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFAFA"))
            )

    zone_table.setStyle(TableStyle(zone_style_cmds))
    elements.append(zone_table)
    elements.append(Spacer(1, 12))

    # ── Embedded charts (try/except) ───────────
    try:
        pie_fig = _build_breakdown_pie_fig(
            data["total_energy"], data["total_human"], data["total_window"]
        )
        bar_fig = _build_zone_bar_fig(data["zone_data"])

        charts_added = False

        if pie_fig is not None:
            png_bytes = _fig_to_png_bytes(pie_fig, width=460, height=260)
            if png_bytes:
                elements.append(Paragraph("Visual Analysis", style_heading))
                charts_added = True
                img_buffer = io.BytesIO(png_bytes)
                img = Image(img_buffer, width=160 * mm, height=90 * mm)
                elements.append(img)
                elements.append(Spacer(1, 8))

        if bar_fig is not None:
            png_bytes = _fig_to_png_bytes(bar_fig, width=460, height=300)
            if png_bytes:
                if not charts_added:
                    elements.append(Paragraph("Visual Analysis", style_heading))
                img_buffer = io.BytesIO(png_bytes)
                img = Image(img_buffer, width=160 * mm, height=104 * mm)
                elements.append(img)
                elements.append(Spacer(1, 8))
    except Exception as exc:
        logger.debug(f"PDF chart embedding skipped: {exc}")

    # ── Cost analysis framework ────────────────
    elements.append(Paragraph("Cost Analysis Framework", style_heading))
    elements.append(
        Paragraph(
            "This report quantifies building inefficiencies using sensor "
            "data and physics-based models. Key cost components:",
            style_body,
        )
    )
    elements.append(Spacer(1, 4))
    bullets = [
        "<b>Energy Cost</b> \u2014 direct electricity consumption "
        "\u00d7 \u20ac/kWh rate",
        "<b>HVAC Waste</b> \u2014 thermal losses from open windows and "
        "suboptimal setpoints",
        "<b>Productivity Impact</b> \u2014 comfort deviation \u00d7 "
        "occupants \u00d7 wage \u00d7 impact factor",
        "<b>Operating Cost</b> = Energy + HVAC Waste + Productivity Impact",
    ]
    for bullet in bullets:
        elements.append(Paragraph(f"\u2022  {bullet}", style_body))
    elements.append(Spacer(1, 16))

    # ── Building photos placeholder ──────────────
    elements.append(Paragraph("Building Reference", style_heading))
    elements.append(
        Paragraph(
            "Building photos will be available in the next release. "
            "The CFT HORSE/Renault facility in Aveiro comprises two floors "
            "with training rooms, social areas, and technical spaces.",
            style_body,
        )
    )
    elements.append(Spacer(1, 12))

    # ── Footer info ────────────────────────────
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            f"PlantaOS \u2014 Building Intelligence Platform  \u00b7  "
            f"Generated automatically  \u00b7  "
            f"Cost per kWh: \u20ac{DEFAULT_AFI_CONFIG.cost_per_kwh}  \u00b7  "
            f"Avg hourly wage: \u20ac{DEFAULT_AFI_CONFIG.avg_hourly_wage}",
            style_small,
        )
    )

    # ── Build with page numbers ────────────────
    def add_page_number(canvas: Any, doc_obj: Any) -> None:
        """Draw page number at the bottom of each page."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(text_tertiary)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawCentredString(A4[0] / 2.0, 12 * mm, text)
        canvas.restoreState()

    doc.build(
        elements,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return buffer.getvalue()


# ═══════════════════════════════════════════════
# HTML Report
# ═══════════════════════════════════════════════


def _build_breakdown_pie(
    total_energy: float, total_human: float, total_window: float
) -> str:
    """Build cost breakdown pie chart as base64 image.

    Args:
        total_energy: Total energy cost.
        total_human: Total productivity impact cost.
        total_window: Total HVAC waste cost.

    Returns:
        HTML img tag or empty string.
    """
    fig = _build_breakdown_pie_fig(total_energy, total_human, total_window)
    if fig is None:
        return ""
    src = _fig_to_base64(fig)
    if src:
        return (
            f'<img src="{src}" style="max-width:100%;height:auto;" '
            f'alt="Cost Breakdown">'
        )
    return ""


def _build_zone_bar(zone_costs: list[dict]) -> str:
    """Build zone ranking bar chart as base64 image.

    Args:
        zone_costs: List of dicts with 'name' and 'cost' keys.

    Returns:
        HTML img tag or empty string.
    """
    if not zone_costs:
        return ""
    # Adapt to use total_cost key expected by _build_zone_bar_fig
    adapted = [
        {"name": z.get("name", ""), "total_cost": z.get("cost", 0)} for z in zone_costs
    ]
    fig = _build_zone_bar_fig(adapted)
    if fig is None:
        return ""
    src = _fig_to_base64(fig, height=400)
    if src:
        return (
            f'<img src="{src}" style="max-width:100%;height:auto;" alt="Zone Ranking">'
        )
    return ""


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
    data = _get_report_data(period, target_date)

    # Build zone table rows
    zone_rows: list[str] = []
    for zd in data["zone_data"]:
        zone_rows.append(
            f"<tr>"
            f"<td>{zd['name']}</td>"
            f"<td class='num'>\u20ac{zd['energy_cost']:.2f}</td>"
            f"<td class='num'>\u20ac{zd['human_cost']:.2f}</td>"
            f"<td class='num'>\u20ac{zd['window_cost']:.2f}</td>"
            f"<td class='num'><b>\u20ac{zd['total_cost']:.2f}</b></td>"
            f"</tr>"
        )
    zone_table = "\n".join(zone_rows)

    # Energy summary
    energy_summary = ""
    if data["total_kwh"] > 0:
        energy_summary = (
            f"<p>Total consumption: <b>{data['total_kwh']:.1f} kWh</b> "
            f"(avg {data['avg_daily_kwh']:.1f} kWh/day)</p>"
        )

    # Build zone costs for charts
    zone_costs = [
        {"name": zd["name"], "cost": zd["total_cost"]} for zd in data["zone_data"]
    ]

    # Render embedded chart images
    pie_chart_html = _build_breakdown_pie(
        data["total_energy"], data["total_human"], data["total_window"]
    )
    bar_chart_html = _build_zone_bar(zone_costs)

    charts_section = ""
    if pie_chart_html or bar_chart_html:
        charts_section = '<h2>Visual Analysis</h2><div class="chart-row">'
        if pie_chart_html:
            charts_section += f'<div class="chart-box">{pie_chart_html}</div>'
        if bar_chart_html:
            charts_section += f'<div class="chart-box">{bar_chart_html}</div>'
        charts_section += "</div>"

    total_energy = data["total_energy"]
    total_human = data["total_human"]
    total_window = data["total_window"]
    total_cost = data["total_cost"]
    baseline = data["baseline"]
    savings = data["savings"]
    period_label = data["period_label"]
    now_str = data["generated_at"]

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
  .chart-row {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 24px 0; }}
  .chart-box {{ flex: 1; min-width: 300px; }}
  .chart-box img {{ border-radius: 8px; border: 1px solid #E5E5EA; }}
  .print-hint {{ background: #E8F0FE; color: #0071E3; padding: 12px 16px;
                  border-radius: 8px; font-size: 13px; margin-bottom: 24px; }}
  @media print {{
    body {{ margin: 20px; font-size: 11px; }}
    .print-hint {{ display: none; }}
    .kpi-row {{ gap: 8px; }}
    .kpi-box {{ padding: 10px; }}
    h1 {{ font-size: 20px; }}
    h2 {{ font-size: 15px; margin-top: 20px; }}
    table {{ font-size: 11px; }}
    .chart-row {{ page-break-inside: avoid; }}
    .footer {{ font-size: 9px; }}
    @page {{ margin: 15mm; }}
  }}
</style>
</head>
<body>
<div class="print-hint">To save as PDF: press Ctrl+P (or Cmd+P on Mac) and select "Save as PDF".</div>
<h1>PlantaOS Financial Report</h1>
<p class="subtitle">Centro de Forma\u00e7\u00e3o T\u00e9cnica HORSE/Renault \u2014 Aveiro, Portugal</p>
<p class="subtitle">Period: {period_label} \u00b7 Generated: {now_str}</p>

<div class="kpi-row">
  <div class="kpi-box">
    <div class="kpi-value">\u20ac{total_energy:.0f}</div>
    <div class="kpi-label">Energy Cost</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value">\u20ac{total_human:.0f}</div>
    <div class="kpi-label">Productivity Impact</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value">\u20ac{total_window:.0f}</div>
    <div class="kpi-label">HVAC Waste</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-value savings">\u20ac{savings:+.0f}</div>
    <div class="kpi-label">Net Savings vs Baseline</div>
  </div>
</div>

<h2>Energy Summary</h2>
{energy_summary}
<p>Total operating cost: <b class="cost">\u20ac{total_cost:.2f}</b> over {period_label.lower()}</p>
<p>Estimated baseline: \u20ac{baseline:.2f} \u00b7 Savings: <span class="savings">\u20ac{savings:.2f}</span></p>

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
  <td class="num">\u20ac{total_energy:.2f}</td>
  <td class="num">\u20ac{total_human:.2f}</td>
  <td class="num">\u20ac{total_window:.2f}</td>
  <td class="num">\u20ac{total_cost:.2f}</td>
</tr>
</table>

<h2>Cost Analysis Framework</h2>
<p>This report quantifies building inefficiencies using sensor data and
physics-based models. Key cost components:</p>
<ul>
  <li><b>Energy Cost</b> \u2014 direct electricity consumption \u00d7 \u20ac/kWh rate</li>
  <li><b>HVAC Waste</b> \u2014 thermal losses from open windows and suboptimal setpoints</li>
  <li><b>Productivity Impact</b> \u2014 comfort deviation \u00d7 occupants \u00d7 wage \u00d7 impact factor</li>
  <li><b>Operating Cost</b> = Energy + HVAC Waste + Productivity Impact</li>
</ul>

{charts_section}

<div class="footer">
  PlantaOS \u2014 Building Intelligence Platform \u00b7 Generated automatically \u00b7
  Cost per kWh: \u20ac{DEFAULT_AFI_CONFIG.cost_per_kwh} \u00b7
  Avg hourly wage: \u20ac{DEFAULT_AFI_CONFIG.avg_hourly_wage}
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
    data = _get_report_data(period)
    lines = [
        "Zone,Energy (\u20ac),Productivity Impact (\u20ac),"
        "HVAC Waste (\u20ac),Total (\u20ac)"
    ]

    for zd in data["zone_data"]:
        lines.append(
            f"{zd['name']},{zd['energy_cost']:.2f},"
            f"{zd['human_cost']:.2f},{zd['window_cost']:.2f},"
            f"{zd['total_cost']:.2f}"
        )

    return "\n".join(lines)
