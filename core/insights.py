"""AI-powered insights via Claude API.

Sends anomaly context and building state to the Anthropic API
and returns natural language explanations and recommendations.
Falls back to template-based insights if the API is unavailable.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from loguru import logger

from config.building import get_zone_by_id
from config.settings import settings
from data.store import store

# Rate limiting: max 1 API call per 5 minutes
_last_api_call: float = 0.0
_API_COOLDOWN_SECONDS = 300

# System prompt for PlantaOS insight generation
_SYSTEM_PROMPT = """You are PlantaOS, the intelligent operating system for the Centro de Formação \
Técnica HORSE/Renault in Aveiro, Portugal. You analyze building sensor data and \
provide concise, actionable insights.

Your role:
- Explain anomalies in plain language (Portuguese or English based on context)
- Identify root causes when possible
- Suggest specific corrective actions
- Reference zone names and building layout when relevant
- Keep insights concise (2-4 sentences)
- Focus on what matters to facility managers

Building context:
- 2-floor training center, ~1000m², max 454 occupants
- Two shifts: morning (6h-14h), afternoon (14h-22h)
- HVAC, lighting, comfort sensors across 20 monitored zones
- March weather in Aveiro: 8-18°C, occasional rain"""


def generate_insight(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Generate a natural language insight for an anomaly.

    Sends context to Claude API and returns an explanation with
    recommendations. Falls back to a template if API is unavailable.

    Args:
        anomaly: Dict describing the anomaly (zone, metric, value,
            baseline, severity, etc.).
        context: Optional building-wide context for richer insights.

    Returns:
        Natural language insight string.
    """
    prompt = _build_prompt(anomaly, context)

    try:
        return _call_claude_api(prompt)
    except Exception as e:
        logger.debug(f"API unavailable, using fallback: {e}")
        return _fallback_insight(anomaly)


def generate_daily_summary(target_date: date | None = None) -> str:
    """Generate a natural language summary for a day.

    Args:
        target_date: Date to summarize. Defaults to today.

    Returns:
        Summary string with key findings and recommendations.
    """
    if target_date is None:
        target_date = date.today()

    # Gather day's data
    energy_df = store.get("energy")
    comfort_df = store.get("comfort")
    occ_df = store.get("occupancy")
    weather_df = store.get("weather")

    summary_parts = [f"Daily Summary — {target_date.strftime('%d %B %Y')}"]

    if energy_df is not None and not energy_df.empty:
        day_energy = energy_df[energy_df["timestamp"].dt.date == target_date][
            "total_kwh"
        ].sum()
        summary_parts.append(f"Total energy consumption: {day_energy:.1f} kWh")

    if occ_df is not None and not occ_df.empty:
        day_occ = occ_df[occ_df["timestamp"].dt.date == target_date]
        if not day_occ.empty:
            peak = day_occ.groupby("timestamp")["occupant_count"].sum().max()
            summary_parts.append(f"Peak building occupancy: {peak} people")

    if comfort_df is not None and not comfort_df.empty:
        day_comfort = comfort_df[comfort_df["timestamp"].dt.date == target_date]
        if not day_comfort.empty:
            avg_temp = day_comfort["temperature_c"].mean()
            avg_co2 = day_comfort["co2_ppm"].mean()
            summary_parts.append(
                f"Average temperature: {avg_temp:.1f}°C, CO2: {avg_co2:.0f} ppm"
            )

    if weather_df is not None and not weather_df.empty:
        day_weather = weather_df[weather_df["timestamp"].dt.date == target_date]
        if not day_weather.empty:
            outdoor_temp = day_weather["outdoor_temp_c"].mean()
            rain_pct = day_weather["is_raining"].mean() * 100
            summary_parts.append(
                f"Outdoor: {outdoor_temp:.1f}°C avg, {rain_pct:.0f}% rain periods"
            )

    # Try Claude API for richer summary
    context_text = "\n".join(summary_parts)
    prompt = (
        f"Based on this building data, provide a brief 3-4 sentence summary "
        f"highlighting key findings and any recommendations:\n\n{context_text}"
    )

    try:
        return _call_claude_api(prompt)
    except Exception:
        return "\n".join(summary_parts)


def generate_zone_analysis(zone_id: str) -> str:
    """Generate a detailed analysis for a specific zone.

    Args:
        zone_id: Zone to analyze.

    Returns:
        Analysis string with metrics, trends, and recommendations.
    """
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id

    parts = [f"Zone Analysis: {zone_name} ({zone_id})"]

    comfort_df = store.get_zone_data("comfort", zone_id)
    if comfort_df is not None and not comfort_df.empty:
        latest = comfort_df.sort_values("timestamp").iloc[-1]
        parts.append(
            f"Current: {latest.get('temperature_c', '?')}°C, "
            f"{latest.get('humidity_pct', '?')}% RH, "
            f"{latest.get('co2_ppm', '?')} ppm CO2, "
            f"{latest.get('illuminance_lux', '?')} lux"
        )

    energy_df = store.get_zone_data("energy", zone_id)
    if energy_df is not None and not energy_df.empty:
        daily_kwh = energy_df.groupby(energy_df["timestamp"].dt.date)["total_kwh"].sum()
        if not daily_kwh.empty:
            parts.append(
                f"Energy: {daily_kwh.mean():.2f} kWh/day avg, "
                f"peak {daily_kwh.max():.2f} kWh/day"
            )

    occ_df = store.get_zone_data("occupancy", zone_id)
    if occ_df is not None and not occ_df.empty:
        parts.append(
            f"Occupancy: avg {occ_df['occupant_count'].mean():.1f}, "
            f"peak {occ_df['occupant_count'].max()}"
        )

    # Try API
    prompt = (
        "Analyze this zone data and provide 2-3 actionable insights:\n\n"
        + "\n".join(parts)
    )

    try:
        return _call_claude_api(prompt)
    except Exception:
        return "\n".join(parts)


def _build_prompt(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Construct the prompt for the Claude API.

    Args:
        anomaly: Anomaly details.
        context: Building context.

    Returns:
        Formatted prompt string.
    """
    zone_id = anomaly.get("zone_id", "unknown")
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id

    parts = [
        f"Anomaly detected in {zone_name} ({zone_id}):",
        f"  Metric: {anomaly.get('metric', 'unknown')}",
        f"  Current value: {anomaly.get('value', '?')}",
        f"  Expected value: {anomaly.get('expected', '?')}",
        f"  Deviation: {anomaly.get('deviation', '?')}σ",
        f"  Severity: {anomaly.get('severity', 'unknown')}",
    ]

    if context:
        parts.append("\nBuilding context:")
        if "total_occupancy" in context:
            parts.append(f"  Total occupancy: {context['total_occupancy']}")
        if "outdoor_temp" in context:
            parts.append(f"  Outdoor temperature: {context['outdoor_temp']}°C")
        if "is_raining" in context:
            parts.append(f"  Raining: {'Yes' if context['is_raining'] else 'No'}")

    parts.append(
        "\nExplain this anomaly, identify the likely cause, "
        "and suggest a corrective action in 2-3 sentences."
    )

    return "\n".join(parts)


def _call_claude_api(prompt: str) -> str:
    """Call the Anthropic Claude API.

    Args:
        prompt: The prompt to send.

    Returns:
        Response text from Claude.

    Raises:
        RuntimeError: If API key is missing or rate limit exceeded.
    """
    global _last_api_call

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    # Rate limiting
    now = time.time()
    if now - _last_api_call < _API_COOLDOWN_SECONDS:
        remaining = _API_COOLDOWN_SECONDS - (now - _last_api_call)
        raise RuntimeError(f"Rate limited, try again in {remaining:.0f}s")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    _last_api_call = time.time()

    return message.content[0].text


def _fallback_insight(anomaly: dict[str, Any]) -> str:
    """Generate a template-based insight when API is unavailable.

    Args:
        anomaly: Anomaly details.

    Returns:
        Template-based insight string.
    """
    zone_id = anomaly.get("zone_id", "unknown")
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    metric = anomaly.get("metric", "unknown")
    value = anomaly.get("value", "?")
    expected = anomaly.get("expected", "?")
    severity = anomaly.get("severity", "info")
    deviation = anomaly.get("deviation", 0)

    templates = {
        "temperature": (
            f"Temperature in {zone_name} is {value}°C "
            f"(expected ~{expected}°C, {abs(deviation):.1f}σ deviation). "
            f"{'Check HVAC system operation and thermostat settings.' if severity != 'info' else 'Minor variation within normal range.'}"
        ),
        "humidity": (
            f"Humidity in {zone_name} is at {value}% "
            f"(expected ~{expected}%, {abs(deviation):.1f}σ deviation). "
            f"{'Check for open windows or ventilation issues.' if severity != 'info' else 'Within acceptable range.'}"
        ),
        "co2": (
            f"CO2 levels in {zone_name} are {value} ppm "
            f"(expected ~{expected} ppm). "
            f"{'Increase ventilation or check air handling unit.' if severity != 'info' else 'CO2 levels are normal.'}"
        ),
        "illuminance": (
            f"Light levels in {zone_name} are {value} lux "
            f"(expected ~{expected} lux). "
            f"{'Check lighting controls and window shading.' if severity != 'info' else 'Lighting is adequate.'}"
        ),
        "energy": (
            f"Energy consumption in {zone_name} is {value} kWh "
            f"(expected ~{expected} kWh, {abs(deviation):.1f}σ deviation). "
            f"{'Investigate for equipment left running or HVAC malfunction.' if severity != 'info' else 'Consumption is within normal range.'}"
        ),
    }

    # Match metric to template key
    template_key = metric
    for key in templates:
        if key in metric.lower():
            template_key = key
            break

    return templates.get(
        template_key,
        f"Anomaly detected in {zone_name}: {metric} = {value} "
        f"(expected {expected}, severity: {severity}). "
        f"Review sensor data and check zone conditions.",
    )
