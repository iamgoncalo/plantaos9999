"""AI-powered insights via Claude API.

Sends anomaly context and building state to the Anthropic API
and returns structured Insight models with titles, explanations,
and recommended actions. Falls back to template-based insights
if the API is unavailable.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel

from config.building import get_zone_by_id
from config.settings import settings
from data.store import store

# Rate limiting: max 1 API call per 5 minutes
_last_api_call: float = 0.0
_API_COOLDOWN_SECONDS = 300

# Change detection for insight generation
_last_state_hash: str = ""

# System prompt for PlantaOS insight generation
_SYSTEM_PROMPT = """You are PlantaOS, the intelligent operating system for the Centro de Formação \
Técnica HORSE/Renault in Aveiro, Portugal. You analyze building sensor data and \
provide concise, actionable insights.

You have access to the AFI (Architecture of Freedom Intelligence) framework:
- Perception (P): sensor coverage quality — P = log2(N) * T where N=exits, T=sensor depth
- Distortion (D): barriers to free movement — geometric model of temperature, CO2, crowding
- Freedom (F = P/D): the spatial health index (higher is better)
- Financial Bleed: €/hr cost of inefficiencies (energy waste + human capital loss)
- Stigmergy: pheromone-based routing through zone adjacency graph

Your role:
- Explain anomalies in plain language (Portuguese or English based on context)
- Identify root causes when possible, citing specific €/hr costs
- Suggest specific corrective actions with expected savings
- Reference zone names, Freedom scores, and financial bleed when relevant
- Keep insights concise (2-4 sentences)
- Focus on what matters to facility managers

Building context:
- 2-floor training center, ~1000m², max 454 occupants
- Two shifts: morning (6h-14h), afternoon (14h-22h)
- HVAC, lighting, comfort sensors across 20 monitored zones
- March weather in Aveiro: 8-18°C, occasional rain
- 3 sensor tiers: Cheap IoT (T=1h), Matter Compliant (T=4h), AI Vision (T=8h)"""


class Insight(BaseModel):
    """A structured AI-generated insight about building operations."""

    title: str
    explanation: str
    severity: str = "info"  # 'info', 'warning', 'critical'
    affected_zones: list[str] = []
    recommended_action: str = ""
    category: str = "general"  # 'energy', 'comfort', 'occupancy', 'general'
    timestamp: str = ""


def state_has_changed(state_data: dict) -> bool:
    """Check if building state has changed significantly.

    Args:
        state_data: Building state dict from BuildingState.model_dump().

    Returns:
        True if state changed enough to warrant new insights.
    """
    global _last_state_hash
    key = (
        f"{state_data.get('active_alerts', 0)}_"
        f"{state_data.get('total_energy_kwh', 0):.0f}_"
        f"{state_data.get('avg_freedom_index', 0):.0f}"
    )
    if key == _last_state_hash:
        return False
    _last_state_hash = key
    return True


def generate_insight(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> Insight:
    """Generate a structured insight for an anomaly.

    Sends context to Claude API and returns an Insight model.
    Falls back to a template if API is unavailable.

    Args:
        anomaly: Dict describing the anomaly (zone, metric, value,
            baseline, severity, etc.).
        context: Optional building-wide context for richer insights.

    Returns:
        Insight model with title, explanation, and recommendation.
    """
    prompt = _build_structured_prompt(anomaly, context)
    now_str = datetime.now().isoformat()
    zone_id = anomaly.get("zone_id", "unknown")
    metric = anomaly.get("metric", "unknown")
    severity = anomaly.get("severity", "info")
    category = _metric_to_category(metric)

    try:
        response = _call_claude_api(prompt)
        return _parse_insight_response(response, zone_id, severity, category, now_str)
    except Exception as e:
        logger.debug(f"API unavailable, using fallback: {e}")
        return _fallback_insight(anomaly, now_str)


def generate_building_insights(
    building_state_data: dict,
) -> list[Insight]:
    """Scan building state for anomalous zones and generate insights.

    Uses mock engine when API key is not configured, otherwise
    attempts the Claude API with fallback to templates.

    Args:
        building_state_data: Building state dict from
            BuildingState.model_dump(mode="json").

    Returns:
        List of Insight models for zones with warning/critical status.
    """
    # Use mock engine when API key is not available
    if not settings.ANTHROPIC_API_KEY:
        logger.debug("No API key configured, using mock insight engine")
        return _generate_mock_insights(building_state_data)

    insights: list[Insight] = []
    now_str = datetime.now().isoformat()

    for floor_state in building_state_data.get("floors", []):
        for zone in floor_state.get("zones", []):
            status = zone.get("status", "unknown")
            if status not in ("warning", "critical"):
                continue

            zone_id = zone.get("zone_id", "unknown")
            zone_info = get_zone_by_id(zone_id)
            zone_name = zone_info.name if zone_info else zone_id

            # Build anomaly dict from zone state
            anomaly_data = _zone_state_to_anomaly(zone, zone_name)

            # Context from building state
            ctx = {
                "total_occupancy": building_state_data.get("total_occupancy", 0),
            }

            # Try Claude for first insight, fallback for the rest
            if not insights:
                insight = generate_insight(anomaly_data, ctx)
            else:
                insight = _fallback_insight(anomaly_data, now_str)

            insights.append(insight)

    # If no anomalous zones, generate a healthy building insight
    if not insights:
        freedom = building_state_data.get("avg_freedom_index", 0)
        energy = building_state_data.get("total_energy_kwh", 0)
        occ = building_state_data.get("total_occupancy", 0)
        insights.append(
            Insight(
                title="Building operating normally",
                explanation=(
                    f"All zones are within acceptable parameters. "
                    f"Building health index is {freedom:.0f}/100 with "
                    f"{occ} people and {energy:.1f} kWh total consumption."
                ),
                severity="info",
                category="general",
                timestamp=now_str,
            )
        )

    return insights


def answer_building_question(
    question: str,
    building_state: dict | None = None,
) -> str:
    """Answer a user question about the building using Claude.

    Args:
        question: User's natural language question.
        building_state: Current building state for context.

    Returns:
        Answer string from Claude or fallback message.
    """
    # Build context summary
    ctx_parts = ["Current building state:"]

    if building_state:
        ctx_parts.append(
            f"  Total occupancy: {building_state.get('total_occupancy', '?')}"
        )
        ctx_parts.append(
            f"  Total energy: {building_state.get('total_energy_kwh', 0):.1f} kWh"
        )
        ctx_parts.append(
            f"  Building health: {building_state.get('avg_freedom_index', 0):.0f}/100"
        )
        ctx_parts.append(f"  Active alerts: {building_state.get('active_alerts', 0)}")

        # AFI data
        bleed = building_state.get("total_financial_bleed_eur_hr", 0)
        afi_f = building_state.get("avg_afi_freedom", 0)
        if bleed or afi_f:
            ctx_parts.append(f"  AFI Freedom: {afi_f:.1f}")
            ctx_parts.append(f"  Financial Bleed: €{bleed:.2f}/hr")

        for floor in building_state.get("floors", []):
            floor_num = floor.get("floor", "?")
            ctx_parts.append(
                f"\n  Floor {floor_num}: "
                f"{floor.get('avg_temperature', 0):.1f}°C avg, "
                f"{floor.get('total_occupancy', 0)} people, "
                f"{floor.get('total_energy_kwh', 0):.1f} kWh"
            )
            for z in floor.get("zones", []):
                zone_info = get_zone_by_id(z["zone_id"])
                name = zone_info.name if zone_info else z["zone_id"]
                z_bleed = z.get("financial_bleed_eur_hr", 0)
                z_freedom = z.get("afi_freedom", 0)
                if z.get("status") in ("warning", "critical"):
                    ctx_parts.append(
                        f"    ⚠ {name}: {z.get('status')} — "
                        f"{z.get('temperature_c', '?')}°C, "
                        f"CO₂ {z.get('co2_ppm', '?')} ppm"
                        f"{f', F={z_freedom:.1f}, €{z_bleed:.2f}/hr' if z_bleed else ''}"
                    )

    context_text = "\n".join(ctx_parts)
    prompt = (
        f"{context_text}\n\n"
        f"User question: {question}\n\n"
        f"Answer concisely (2-4 sentences), referencing specific zones "
        f"and metrics where relevant."
    )

    # Use mock chat when API key is not available
    if not settings.ANTHROPIC_API_KEY:
        logger.debug("No API key configured, using mock chat engine")
        return _mock_chat_response(question, building_state)

    try:
        return _call_claude_api(prompt)
    except Exception as e:
        logger.debug(f"Chat API unavailable: {e}")
        return _mock_chat_response(question, building_state)


def generate_daily_summary(target_date: date | None = None) -> str:
    """Generate a natural language summary for a day.

    Args:
        target_date: Date to summarize. Defaults to today.

    Returns:
        Summary string with key findings and recommendations.
    """
    if target_date is None:
        target_date = date.today()

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

    prompt = (
        "Analyze this zone data and provide 2-3 actionable insights:\n\n"
        + "\n".join(parts)
    )

    try:
        return _call_claude_api(prompt)
    except Exception:
        return "\n".join(parts)


# ── Mock engine (no API key) ────────────────────────


def _generate_mock_insights(state_data: dict) -> list[Insight]:
    """Pattern-match on building state to generate realistic insights.

    Scans zone data for comfort, energy, and occupancy anomalies and
    produces data-aware insight objects without calling the API.

    Args:
        state_data: Building state dict from BuildingState.model_dump().

    Returns:
        Up to 5 Insight models, prioritized critical > warning > info.
    """
    now_str = datetime.now().isoformat()
    candidates: list[Insight] = []

    try:
        for floor_state in state_data.get("floors", []):
            for zone in floor_state.get("zones", []):
                zone_id = zone.get("zone_id", "unknown")
                zone_info = get_zone_by_id(zone_id)
                zone_name = zone_info.name if zone_info else zone_id
                capacity = zone_info.capacity if zone_info else 0

                co2 = zone.get("co2_ppm")
                temp = zone.get("temperature_c")
                energy = zone.get("total_energy_kwh", 0.0)
                occ = zone.get("occupant_count", 0)
                status = zone.get("status", "unknown")

                # High CO2
                if co2 is not None and co2 > 1000:
                    candidates.append(
                        Insight(
                            title=f"Elevated CO2 in {zone_name}",
                            explanation=(
                                f"CO2 levels in {zone_name} have reached "
                                f"{co2:.0f} ppm, exceeding the 1000 ppm threshold. "
                                f"Increase ventilation rate or reduce occupancy."
                            ),
                            severity="warning",
                            affected_zones=[zone_id],
                            recommended_action=(
                                "Increase mechanical ventilation or open windows "
                                "to improve air circulation."
                            ),
                            category="comfort",
                            timestamp=now_str,
                        )
                    )

                # Temperature out of range
                if temp is not None and (temp > 26 or temp < 18):
                    if temp > 30 or temp < 15:
                        sev = "critical"
                    else:
                        sev = "warning"
                    if temp > 26:
                        action = "Reduce HVAC setpoint or check cooling system."
                    else:
                        action = "Increase HVAC setpoint or check heating system."
                    candidates.append(
                        Insight(
                            title=f"Temperature alert in {zone_name}",
                            explanation=(
                                f"{zone_name} temperature is {temp:.1f} C, "
                                f"outside the optimal 20-24 C range. {action}"
                            ),
                            severity=sev,
                            affected_zones=[zone_id],
                            recommended_action=action,
                            category="comfort",
                            timestamp=now_str,
                        )
                    )

                # High energy consumption
                if energy is not None and energy > 2.0:
                    candidates.append(
                        Insight(
                            title=f"High energy usage in {zone_name}",
                            explanation=(
                                f"{zone_name} energy consumption ({energy:.1f} kWh) "
                                f"is elevated. Consider reviewing HVAC schedule "
                                f"for off-peak optimization."
                            ),
                            severity="info",
                            affected_zones=[zone_id],
                            recommended_action=(
                                "Review HVAC and lighting schedules for "
                                "potential off-peak savings."
                            ),
                            category="energy",
                            timestamp=now_str,
                        )
                    )

                # Low utilization
                if occ is not None and occ < 3 and status != "unknown" and capacity > 0:
                    util = (occ / capacity * 100) if capacity > 0 else 0
                    candidates.append(
                        Insight(
                            title=f"Low utilization in {zone_name}",
                            explanation=(
                                f"{zone_name} has only {occ} occupants in a "
                                f"{capacity}-person space ({util:.0f}% utilization). "
                                f"Consider consolidating activities to reduce "
                                f"energy waste."
                            ),
                            severity="info",
                            affected_zones=[zone_id],
                            recommended_action=(
                                "Consolidate activities into fewer zones and "
                                "reduce HVAC/lighting in unoccupied areas."
                            ),
                            category="occupancy",
                            timestamp=now_str,
                        )
                    )

                # High occupancy
                if occ is not None and capacity > 0 and occ > capacity * 0.9:
                    candidates.append(
                        Insight(
                            title=f"Near capacity in {zone_name}",
                            explanation=(
                                f"{zone_name} is near capacity ({occ}/{capacity}). "
                                f"Consider redirecting overflow to alternative spaces."
                            ),
                            severity="warning",
                            affected_zones=[zone_id],
                            recommended_action=(
                                "Redirect occupants to underutilized zones "
                                "to maintain comfort and safety."
                            ),
                            category="occupancy",
                            timestamp=now_str,
                        )
                    )

    except Exception as exc:
        logger.warning(f"Error generating mock insights: {exc}")

    # Prioritize: critical > warning > info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    candidates.sort(key=lambda i: severity_order.get(i.severity, 3))

    # Return max 5 insights, or a healthy-building message
    if candidates:
        return candidates[:5]

    freedom = state_data.get("avg_freedom_index", 0)
    energy = state_data.get("total_energy_kwh", 0)
    occ = state_data.get("total_occupancy", 0)
    return [
        Insight(
            title="Building operating normally",
            explanation=(
                f"All zones are within acceptable parameters. "
                f"Building health index is {freedom:.0f}/100 with "
                f"{occ} people and {energy:.1f} kWh total consumption."
            ),
            severity="info",
            category="general",
            timestamp=now_str,
        )
    ]


def _mock_chat_response(
    question: str,
    state_data: dict | None,
) -> str:
    """Generate a data-aware chat response without the API.

    Parses common question patterns and responds with building
    metrics extracted from the current state data.

    Args:
        question: User's natural language question.
        state_data: Current building state dict, or None.

    Returns:
        A contextual response string based on available data.
    """
    try:
        q = question.lower()

        # Collect zone-level data for analysis
        zones: list[dict] = []
        if state_data:
            for floor in state_data.get("floors", []):
                for z in floor.get("zones", []):
                    zone_info = get_zone_by_id(z.get("zone_id", ""))
                    z["_name"] = zone_info.name if zone_info else z.get("zone_id", "?")
                    z["_capacity"] = zone_info.capacity if zone_info else 0
                    zones.append(z)

        total_occ = state_data.get("total_occupancy", 0) if state_data else 0
        total_kwh = state_data.get("total_energy_kwh", 0) if state_data else 0
        avg_freedom = state_data.get("avg_freedom_index", 0) if state_data else 0
        n_alerts = state_data.get("active_alerts", 0) if state_data else 0

        # Temperature questions
        if any(kw in q for kw in ("temperature", "temp", "hot", "cold")):
            temps = [
                (z["_name"], z["temperature_c"])
                for z in zones
                if z.get("temperature_c") is not None
            ]
            if not temps:
                return "No temperature data is currently available."
            avg_temp = sum(t for _, t in temps) / len(temps)
            out_of_range = [f"{n} ({t:.1f} C)" for n, t in temps if t > 24 or t < 20]
            msg = f"The average building temperature is {avg_temp:.1f} C."
            if out_of_range:
                msg += (
                    f" Zones outside the 20-24 C comfort range: "
                    f"{', '.join(out_of_range)}."
                )
            else:
                msg += " All zones are within the 20-24 C comfort range."
            return msg

        # Energy questions
        if any(kw in q for kw in ("energy", "consumption", "kwh")):
            energy_zones = [(z["_name"], z.get("total_energy_kwh", 0)) for z in zones]
            energy_zones.sort(key=lambda x: x[1], reverse=True)
            msg = f"Total building energy consumption is {total_kwh:.1f} kWh."
            if energy_zones:
                top = energy_zones[0]
                msg += f" Highest consumer: {top[0]} at {top[1]:.1f} kWh."
            return msg

        # Occupancy questions
        if any(kw in q for kw in ("occupancy", "people", "empty", "utilization")):
            occ_zones = [
                (z["_name"], z.get("occupant_count", 0), z["_capacity"])
                for z in zones
                if z["_capacity"] > 0
            ]
            occ_zones.sort(key=lambda x: x[1], reverse=True)
            msg = f"Current total building occupancy is {total_occ} people."
            if occ_zones:
                busiest = occ_zones[0]
                emptiest = occ_zones[-1]
                msg += (
                    f" Busiest zone: {busiest[0]} with {busiest[1]} occupants. "
                    f"Emptiest zone: {emptiest[0]} with {emptiest[1]} occupants."
                )
            return msg

        # CO2 / air quality questions
        if any(kw in q for kw in ("co2", "air quality", "ventilation")):
            co2_zones = [
                (z["_name"], z["co2_ppm"])
                for z in zones
                if z.get("co2_ppm") is not None
            ]
            if not co2_zones:
                return "No CO2 data is currently available."
            co2_zones.sort(key=lambda x: x[1], reverse=True)
            worst = co2_zones[0]
            return (
                f"The zone with highest CO2 is {worst[0]} at {worst[1]:.0f} ppm. "
                f"{'This exceeds the 1000 ppm recommended threshold.' if worst[1] > 1000 else 'This is within acceptable levels.'}"
            )

        # Cost / savings questions
        if any(kw in q for kw in ("cost", "money", "save", "expense", "budget")):
            bleed = (
                state_data.get("total_financial_bleed_eur_hr", 0) if state_data else 0
            )
            energy_zones = [(z["_name"], z.get("total_energy_kwh", 0)) for z in zones]
            energy_zones.sort(key=lambda x: x[1], reverse=True)
            msg = (
                f"Current operating cost (financial bleed) is "
                f"{bleed:.2f} EUR/hr with total energy at {total_kwh:.1f} kWh."
            )
            if energy_zones:
                msg += (
                    f" Top zone for potential savings: {energy_zones[0][0]} "
                    f"consuming {energy_zones[0][1]:.1f} kWh."
                )
            return msg

        # Alert / warning questions
        if any(kw in q for kw in ("alert", "warning", "problem")):
            problem_zones = [
                f"{z['_name']} ({z.get('status', '?')})"
                for z in zones
                if z.get("status") in ("warning", "critical")
            ]
            if problem_zones:
                return (
                    f"There are {n_alerts} active alerts. "
                    f"Affected zones: {', '.join(problem_zones)}."
                )
            return "No active alerts. All zones are operating within normal parameters."

        # Health / score questions
        if any(kw in q for kw in ("health", "score", "performance")):
            return (
                f"The average building health score is {avg_freedom:.0f}/100 "
                f"with {total_occ} occupants and {n_alerts} active alerts. "
                f"Total energy consumption is {total_kwh:.1f} kWh."
            )

        # Default fallback
        n_zones = len(zones)
        temps = [
            z["temperature_c"] for z in zones if z.get("temperature_c") is not None
        ]
        avg_temp = sum(temps) / len(temps) if temps else 0
        return (
            f"Based on current sensor data, the building has {n_zones} active "
            f"zones with {total_occ} total occupants. The average temperature "
            f"is {avg_temp:.1f} C and total energy usage is {total_kwh:.1f} kWh. "
            f"Ask about specific topics like temperature, energy, costs, or "
            f"air quality for detailed analysis."
        )

    except Exception as exc:
        logger.warning(f"Error in mock chat response: {exc}")
        return (
            "I'm processing your question using offline mode. "
            "Please check the dashboard for current building data."
        )


# ── Private helpers ─────────────────────────────────


def _build_structured_prompt(
    anomaly: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Construct a prompt requesting structured JSON insight.

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

    parts.append("\nRespond ONLY with a JSON object (no markdown, no extra text):")
    parts.append(
        '{"title": "<max 10 words>", '
        '"explanation": "<2-3 sentences>", '
        '"severity": "<info|warning|critical>", '
        '"recommended_action": "<specific action>"}'
    )

    return "\n".join(parts)


def _parse_insight_response(
    response: str,
    zone_id: str,
    severity: str,
    category: str,
    timestamp: str,
) -> Insight:
    """Parse Claude's JSON response into an Insight model.

    Args:
        response: Raw API response text.
        zone_id: Zone the anomaly was detected in.
        severity: Original anomaly severity.
        category: Insight category.
        timestamp: ISO timestamp.

    Returns:
        Parsed Insight model.
    """
    try:
        # Try to extract JSON from response
        text = response.strip()
        # Handle responses wrapped in markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)
        return Insight(
            title=data.get("title", "Anomaly Detected"),
            explanation=data.get("explanation", response),
            severity=data.get("severity", severity),
            affected_zones=[zone_id],
            recommended_action=data.get("recommended_action", ""),
            category=category,
            timestamp=timestamp,
        )
    except (json.JSONDecodeError, KeyError):
        # Fallback: use raw response as explanation
        return Insight(
            title="Anomaly Detected",
            explanation=response[:300],
            severity=severity,
            affected_zones=[zone_id],
            recommended_action="Review zone conditions and sensor data.",
            category=category,
            timestamp=timestamp,
        )


def _zone_state_to_anomaly(zone: dict[str, Any], zone_name: str) -> dict[str, Any]:
    """Convert a zone state dict into an anomaly-style dict.

    Args:
        zone: Zone state from BuildingState.
        zone_name: Display name of the zone.

    Returns:
        Dict formatted for generate_insight().
    """
    # Determine primary metric that triggered the status
    metric = "comfort"
    value: Any = "—"
    expected: Any = "—"

    temp = zone.get("temperature_c")
    co2 = zone.get("co2_ppm")
    humidity = zone.get("humidity_pct")

    if co2 is not None and co2 > 1000:
        metric = "co2_ppm"
        value = co2
        expected = 600
    elif temp is not None and (temp > 26 or temp < 18):
        metric = "temperature_c"
        value = temp
        expected = 22
    elif humidity is not None and (humidity > 70 or humidity < 30):
        metric = "humidity_pct"
        value = humidity
        expected = 50

    return {
        "zone_id": zone.get("zone_id", "unknown"),
        "zone_name": zone_name,
        "metric": metric,
        "value": value,
        "expected": expected,
        "deviation": 2.5,
        "severity": zone.get("status", "warning"),
    }


def _fallback_insight(
    anomaly: dict[str, Any],
    timestamp: str | None = None,
) -> Insight:
    """Generate a template-based insight when API is unavailable.

    Args:
        anomaly: Anomaly details.
        timestamp: ISO timestamp. Defaults to now.

    Returns:
        Insight model with template-based content.
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    zone_id = anomaly.get("zone_id", "unknown")
    zone = get_zone_by_id(zone_id)
    zone_name = zone.name if zone else zone_id
    metric = anomaly.get("metric", "unknown")
    value = anomaly.get("value", "?")
    expected = anomaly.get("expected", "?")
    severity = anomaly.get("severity", "info")
    deviation = anomaly.get("deviation", 0)
    category = _metric_to_category(metric)

    templates: dict[str, tuple[str, str, str]] = {
        "temperature": (
            f"Temperature alert in {zone_name}",
            f"Temperature is {value}°C (expected ~{expected}°C, "
            f"{abs(deviation) if isinstance(deviation, (int, float)) else 0:.1f}σ deviation). "
            f"{'This exceeds comfort thresholds and may affect occupant wellbeing.' if severity != 'info' else 'Minor variation within normal range.'}",
            "Check HVAC system operation and thermostat settings.",
        ),
        "humidity": (
            f"Humidity anomaly in {zone_name}",
            f"Humidity is at {value}% (expected ~{expected}%, "
            f"{abs(deviation) if isinstance(deviation, (int, float)) else 0:.1f}σ deviation). "
            f"{'Out-of-range humidity can affect comfort and equipment.' if severity != 'info' else 'Within acceptable range.'}",
            "Check for open windows or ventilation issues.",
        ),
        "co2": (
            f"CO₂ levels elevated in {zone_name}",
            f"CO₂ levels are {value} ppm (expected ~{expected} ppm). "
            f"{'High CO₂ indicates insufficient ventilation relative to occupancy.' if severity != 'info' else 'CO₂ levels are normal.'}",
            "Increase ventilation or check air handling unit.",
        ),
        "illuminance": (
            f"Lighting anomaly in {zone_name}",
            f"Light levels are {value} lux (expected ~{expected} lux). "
            f"{'Incorrect lighting can reduce productivity and increase energy waste.' if severity != 'info' else 'Lighting is adequate.'}",
            "Check lighting controls and window shading.",
        ),
        "energy": (
            f"Energy spike in {zone_name}",
            f"Energy consumption is {value} kWh (expected ~{expected} kWh, "
            f"{abs(deviation) if isinstance(deviation, (int, float)) else 0:.1f}σ deviation). "
            f"{'Unexplained consumption spikes may indicate equipment issues.' if severity != 'info' else 'Consumption is within normal range.'}",
            "Investigate for equipment left running or HVAC malfunction.",
        ),
    }

    # Match metric to template key
    template_key = metric
    for key in templates:
        if key in metric.lower():
            template_key = key
            break

    if template_key in templates:
        title, explanation, action = templates[template_key]
    else:
        title = f"Anomaly in {zone_name}"
        explanation = (
            f"{metric} = {value} (expected {expected}, severity: {severity}). "
            f"Review sensor data and check zone conditions."
        )
        action = "Review sensor data and investigate zone conditions."

    return Insight(
        title=title,
        explanation=explanation,
        severity=severity,
        affected_zones=[zone_id],
        recommended_action=action,
        category=category,
        timestamp=timestamp,
    )


def _metric_to_category(metric: str) -> str:
    """Map a metric name to an insight category.

    Args:
        metric: Metric name (e.g., 'temperature_c', 'co2_ppm').

    Returns:
        Category string: 'energy', 'comfort', 'occupancy', or 'general'.
    """
    metric_lower = metric.lower()
    if any(k in metric_lower for k in ("kwh", "energy", "power")):
        return "energy"
    if any(k in metric_lower for k in ("temp", "humid", "co2", "illumin", "comfort")):
        return "comfort"
    if any(k in metric_lower for k in ("occupan", "count", "presence")):
        return "occupancy"
    return "general"


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

    client = anthropic.Anthropic(api_key=api_key, timeout=10.0)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    _last_api_call = time.time()

    return message.content[0].text
