"""
modules/ai_engine.py
--------------------
Traffic analysis using HuggingFace Inference API (free tier).
Model: google/flan-t5-large  — instruction-tuned, fast, free on HF Inference API.
Falls back to a deterministic rule-based engine when no API key is provided,
producing realistic KV-specific analysis without any API call.
"""

import requests
import streamlit as st
from datetime import datetime
import random

HF_API_BASE = "https://api-inference.huggingface.co/models"

# Primary model: instruction-following, great for structured text generation
PRIMARY_MODEL   = "google/flan-t5-large"
# Fallback model: smaller, faster
FALLBACK_MODEL  = "google/flan-t5-base"


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(traffic_data: dict, weather_data: dict) -> dict:
    """Structured context dict used by both HF and rule-based engines."""
    hour     = datetime.now().hour
    is_peak  = (7 <= hour <= 9) or (17 <= hour <= 19)
    day_name = datetime.now().strftime("%A")

    roads   = traffic_data.get("roads", [])
    severe  = [r for r in roads if r["status"] == "SEVERE"]
    heavy   = [r for r in roads if r["status"] == "HEAVY"]
    clear   = [r for r in roads if r["status"] == "CLEAR"]

    rain_prob    = weather_data.get("rain_prob_pct", 0)
    avg_speed    = traffic_data.get("avg_speed_kmh", 35)
    incidents    = traffic_data.get("incidents", [])
    temp         = weather_data.get("temp_c", 31)
    wind         = weather_data.get("wind_kmh", 12)
    description  = weather_data.get("description", "partly cloudy")
    visibility   = weather_data.get("visibility_km", 8.0)

    return {
        "hour": hour, "is_peak": is_peak, "day_name": day_name,
        "severe": severe, "heavy": heavy, "clear": clear, "roads": roads,
        "rain_prob": rain_prob, "avg_speed": avg_speed, "incidents": incidents,
        "temp": temp, "wind": wind, "description": description,
        "visibility": visibility,
    }


def _build_hf_prompt(ctx: dict) -> str:
    """
    Build a concise prompt for flan-t5.
    flan-t5 works best with clear task instructions under ~512 tokens.
    """
    severe_names  = ", ".join(r["name"] for r in ctx["severe"])  or "none"
    heavy_names   = ", ".join(r["name"] for r in ctx["heavy"])   or "none"
    clear_names   = ", ".join(r["name"] for r in ctx["clear"])   or "none"
    incident_strs = "; ".join(
        f"{i['type']} at {i['location']}" for i in ctx["incidents"]
    ) or "none"

    prompt = (
        f"You are a Kuala Lumpur traffic analyst. "
        f"Current time: {ctx['hour']:02d}:00, {ctx['day_name']}. "
        f"Peak hour: {'yes' if ctx['is_peak'] else 'no'}. "
        f"Average KL speed: {ctx['avg_speed']} km/h. "
        f"Severely congested roads: {severe_names}. "
        f"Heavily congested roads: {heavy_names}. "
        f"Clear roads: {clear_names}. "
        f"Incidents: {incident_strs}. "
        f"Weather: {ctx['description']}, {ctx['temp']}C, rain probability {ctx['rain_prob']}%, "
        f"wind {ctx['wind']} km/h, visibility {ctx['visibility']} km. "
        f"Write a 3-sentence traffic advisory for Klang Valley commuters:"
    )
    return prompt


# ── HuggingFace Inference API call ───────────────────────────────────────────

def _call_hf_api(api_key: str, model: str, prompt: str,
                  max_new_tokens: int = 200) -> str | None:
    """Call HuggingFace Inference API. Returns generated text or None."""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens":   max_new_tokens,
                "temperature":      0.7,
                "do_sample":        True,
                "top_p":            0.92,
                "repetition_penalty": 1.3,
            },
            "options": {"wait_for_model": True},
        }
        resp = requests.post(
            f"{HF_API_BASE}/{model}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        if isinstance(result, list) and result:
            text = result[0].get("generated_text", "")
        elif isinstance(result, dict):
            text = result.get("generated_text", "")
        else:
            return None

        # flan-t5 echoes the prompt — strip it
        if prompt in text:
            text = text.replace(prompt, "").strip()
        return text.strip() if text.strip() else None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            return "MODEL_LOADING"
        return None
    except Exception:
        return None


# ── Rule-based fallback engine ────────────────────────────────────────────────

def _rule_based_analysis(ctx: dict) -> str:
    """
    Deterministic but realistic analysis built from live data.
    Used when HF API is unavailable or key not provided.
    """
    hour, is_peak = ctx["hour"], ctx["is_peak"]
    severe, heavy = ctx["severe"], ctx["heavy"]
    rain_prob, avg_speed = ctx["rain_prob"], ctx["avg_speed"]
    incidents = ctx["incidents"]

    lines = []

    # ── Overall situation ─────────────────────────────────────────────────────
    if avg_speed < 20:
        overall = f"🔴 **Critical congestion** across Klang Valley — average speed only {avg_speed} km/h."
    elif avg_speed < 35:
        overall = f"🟠 **Heavy traffic** region-wide. Average speed is {avg_speed} km/h, well below the 60 km/h free-flow."
    elif avg_speed < 55:
        overall = f"🟡 **Moderate congestion** in Klang Valley. Average speed {avg_speed} km/h — expect delays on key corridors."
    else:
        overall = f"🟢 **Traffic is flowing well** — average speed {avg_speed} km/h. Good time to travel."

    if is_peak:
        period = "morning rush hour" if 5 <= hour <= 10 else "evening rush hour"
        overall += f" Currently {period} ({hour:02d}:00) — expect above-normal volumes."
    lines.append(f"**Overall Situation**\n{overall}\n")

    # ── Critical hotspots ─────────────────────────────────────────────────────
    hotspot_lines = []
    for r in severe:
        hotspot_lines.append(
            f"- 🔴 **{r['name']}** ({r['route']}): {r['speed_kmh']} km/h — "
            f"severe jam, {r['congestion_pct']}% congested. Allow extra 20–40 min."
        )
    for r in heavy[:3]:
        hotspot_lines.append(
            f"- 🟠 **{r['name']}**: {r['speed_kmh']} km/h — heavy, {r['congestion_pct']}% congested."
        )
    if not hotspot_lines:
        hotspot_lines.append("- No severe hotspots detected at this time.")

    lines.append("**Critical Hotspots**\n" + "\n".join(hotspot_lines) + "\n")

    # ── Route recommendations ─────────────────────────────────────────────────
    fed_bad  = any(r["name"] == "Federal Highway" and r["status"] in ("SEVERE","HEAVY") for r in ctx["roads"])
    kesas_ok = any(r["name"] == "KESAS Highway"   and r["status"] in ("CLEAR","MODERATE") for r in ctx["roads"])
    npe_ok   = any(r["name"] == "NPE Highway"     and r["status"] in ("CLEAR","MODERATE") for r in ctx["roads"])
    ldp_ok   = any(r["name"] == "LDP"             and r["status"] in ("CLEAR","MODERATE") for r in ctx["roads"])
    elite_ok = any(r["name"] == "ELITE Highway"   and r["status"] in ("CLEAR","MODERATE") for r in ctx["roads"])

    rec_lines = []
    if fed_bad:
        alts = []
        if npe_ok:  alts.append("NPE")
        if kesas_ok: alts.append("KESAS")
        alt_str = " or ".join(alts) if alts else "Jalan Damansara"
        rec_lines.append(f"- **PJ → KL City**: Avoid Federal Highway. Use {alt_str} (+5–10 min but less stop-start).")
    else:
        rec_lines.append("- **PJ → KL City**: Federal Highway is acceptable right now.")

    if elite_ok:
        rec_lines.append("- **Subang → Putrajaya/Cyberjaya**: ELITE Highway is clear — recommended.")
    if ldp_ok:
        rec_lines.append("- **Kelana Jaya → Puchong**: LDP is moderate — workable.")
    rec_lines.append("- **Kepong → City**: Use DUKE Highway; MRR2 is congested.")

    lines.append("**Route Recommendations**\n" + "\n".join(rec_lines) + "\n")

    # ── Weather impact ────────────────────────────────────────────────────────
    weather_parts = []
    if rain_prob >= 70:
        weather_parts.append(
            f"⚡ **High rain probability ({rain_prob}%)** — wet roads reduce safe speeds by 20–30%. "
            "Flash flood risk is elevated at Jalan Ampang underpass and low-lying areas of Kepong."
        )
    elif rain_prob >= 45:
        weather_parts.append(
            f"🌧 **Rain possible ({rain_prob}%)** — keep extra following distance; "
            "visibility may drop. Factor an extra 10–15 min into journey times."
        )
    else:
        weather_parts.append(f"☀️ Weather is {ctx['description']} at {ctx['temp']}°C — no significant impact on driving.")

    if ctx["visibility"] < 5:
        weather_parts.append(f"⚠️ Visibility is low ({ctx['visibility']} km) — use headlights and reduce speed.")
    if ctx["wind"] > 40:
        weather_parts.append(f"🌬 Strong winds ({ctx['wind']} km/h) — extra caution for high-sided vehicles on elevated highways.")

    lines.append("**Weather Impact**\n" + " ".join(weather_parts) + "\n")

    # ── Forecast ─────────────────────────────────────────────────────────────
    next_hour = (hour + 1) % 24
    if 7 <= next_hour <= 9:
        forecast = "Congestion will **worsen** as morning peak builds. Depart before 07:30 or after 09:30 if possible."
    elif hour == 9:
        forecast = "Peak is passing — expect gradual improvement over the next 60 minutes."
    elif 11 <= next_hour <= 15:
        forecast = "Midday lull expected — traffic should ease on most corridors."
    elif 16 <= next_hour <= 19:
        forecast = "Evening peak approaching. Federal Highway and MRR2 will worsen significantly by 17:30."
    elif hour >= 20:
        forecast = "Traffic dissipating. Most highways should be clear within 30–60 minutes."
    else:
        forecast = "Conditions expected to remain broadly similar for the next 1–2 hours."

    if rain_prob >= 65 and 14 <= hour <= 18:
        forecast += " Afternoon thunderstorms will amplify evening congestion — allow extra 15–25 min."

    lines.append(f"**Forecast (Next 2 Hours)**\n{forecast}")

    return "\n\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=180)
def get_ai_analysis(hf_api_key: str, traffic_data: dict, weather_data: dict) -> str:
    """
    Generate traffic analysis report.
    1. Try HuggingFace flan-t5-large for AI-generated advisory paragraph.
    2. Wrap with structured rule-based sections for rich display.
    """
    ctx    = _build_context(traffic_data, weather_data)
    prompt = _build_hf_prompt(ctx)

    hf_paragraph = None
    model_used   = "Rule-based engine"

    if hf_api_key:
        # Try primary model
        text = _call_hf_api(hf_api_key, PRIMARY_MODEL, prompt, max_new_tokens=180)
        if text == "MODEL_LOADING":
            # Try fallback
            text = _call_hf_api(hf_api_key, FALLBACK_MODEL, prompt, max_new_tokens=150)

        if text and text != "MODEL_LOADING" and len(text) > 20:
            hf_paragraph = text
            model_used   = "google/flan-t5-large (HuggingFace)"

    # Build structured report
    # structured = _rule_based_analysis(ctx)

    # Prepend HF-generated advisory if available
    # if hf_paragraph:
    #     header = (
    #         f"**🤖 AI Advisory** *(generated by {model_used})*\n"
    #         f"{hf_paragraph}\n\n---\n\n"
    #     )
    # else:
    #     header = (
    #         f"**🤖 AI Advisory** *(rule-based engine — add HF_API_KEY for model inference)*\n\n"
    #     )

    # return header + structured


def ask_traffic_assistant(
    hf_api_key: str,
    question:   str,
    history:    list,
    traffic_data: dict,
    weather_data: dict,
) -> str:
    """
    Conversational assistant using HF flan-t5 + rule-based fallback.
    flan-t5 is not a conversational model, so we inject context into each turn.
    """
    ctx = _build_context(traffic_data, weather_data)

    # Build a self-contained prompt
    severe_names = ", ".join(r["name"] for r in ctx["severe"]) or "none"
    heavy_names  = ", ".join(r["name"] for r in ctx["heavy"])  or "none"
    clear_names  = ", ".join(r["name"] for r in ctx["clear"])  or "none"
    rain_str     = f"{ctx['rain_prob']}% rain probability"
    time_str     = f"{ctx['hour']:02d}:00, {'peak hour' if ctx['is_peak'] else 'off-peak'}"

    prompt = (
        f"You are a Kuala Lumpur traffic advisor. "
        f"Current conditions at {time_str}: "
        f"avg speed {ctx['avg_speed']} km/h, "
        f"severe jams on {severe_names}, heavy on {heavy_names}, clear on {clear_names}. "
        f"Weather: {ctx['description']}, {ctx['temp']}C, {rain_str}. "
        f"Answer this commuter question helpfully and specifically: {question}"
    )

    if hf_api_key:
        text = _call_hf_api(hf_api_key, PRIMARY_MODEL, prompt, max_new_tokens=150)
        if text and text != "MODEL_LOADING" and len(text) > 15:
            return f"🤖 {text}"
        # Fallback to base model
        text = _call_hf_api(hf_api_key, FALLBACK_MODEL, prompt, max_new_tokens=120)
        if text and text != "MODEL_LOADING" and len(text) > 15:
            return f"🤖 {text}"

    # Rule-based fallback per question keyword
    return _rule_based_qa(question, ctx)


def _rule_based_qa(question: str, ctx: dict) -> str:
    """Keyword-based Q&A for common traffic questions."""
    q = question.lower()
    severe_names = [r["name"] for r in ctx["severe"]]
    heavy_names  = [r["name"] for r in ctx["heavy"]]
    clear_names  = [r["name"] for r in ctx["clear"]]
    is_peak      = ctx["is_peak"]
    rain_prob    = ctx["rain_prob"]
    avg_speed    = ctx["avg_speed"]
    hour         = ctx["hour"]

    if any(w in q for w in ["best time","when","depart","leave"]):
        if is_peak:
            return (
                f"⏰ You're currently in peak hour ({hour:02d}:00). "
                f"Best options: depart **now** if urgent (use NPE or KESAS to avoid Federal Hwy), "
                f"or wait until **after 20:00** when traffic fully clears."
            )
        elif hour < 7:
            return "🌙 Early morning — roads are clear. Best time to travel is right now before 07:00."
        else:
            return (
                f"✅ Off-peak right now ({hour:02d}:00). Good time to travel. "
                f"Avg speed is {avg_speed} km/h. Avoid 07:00–09:30 and 17:00–19:30 tomorrow."
            )

    if "federal" in q:
        fed = next((r for r in ctx["roads"] if r["name"] == "Federal Highway"), {})
        status = fed.get("status","–")
        speed  = fed.get("speed_kmh","–")
        if status in ("SEVERE","HEAVY"):
            return (
                f"🔴 Federal Highway is **{status}** right now ({speed} km/h). "
                f"Strong advice: use NPE via Kerinchi or KESAS via Subang instead. "
                f"{'Rain is making it worse.' if rain_prob > 60 else ''}"
            )
        return f"🟡 Federal Highway is {status} ({speed} km/h). Passable but allow extra 10 min."

    if any(w in q for w in ["rain","flood","weather","wet"]):
        if rain_prob >= 70:
            return (
                f"⚡ Rain probability is **{rain_prob}%** — high risk. "
                f"Expect reduced visibility and wet braking distances. "
                f"Flash flood watch at Jalan Ampang underpass and Kepong low-lying roads. "
                f"Add 15–25 min to all journey times."
            )
        elif rain_prob >= 45:
            return f"🌧 Rain possible ({rain_prob}%). Carry an umbrella and allow 10 extra minutes. No severe flood risk currently."
        return f"☀️ Rain probability is low ({rain_prob}%). Weather should not significantly impact your journey."

    if any(w in q for w in ["subang","cyberjaya","putrajaya","elite"]):
        elite = next((r for r in ctx["roads"] if r["name"] == "ELITE Highway"), {})
        return (
            f"🟢 ELITE Highway is currently **{elite.get('status','–')}** "
            f"({elite.get('speed_kmh','–')} km/h). "
            f"Best route Subang → Putrajaya/Cyberjaya. MEX is also clear."
        )

    if any(w in q for w in ["kepong","mrr2","cheras"]):
        mrr2 = next((r for r in ctx["roads"] if r["name"] == "MRR2"), {})
        return (
            f"🟠 MRR2 is **{mrr2.get('status','–')}** ({mrr2.get('speed_kmh','–')} km/h). "
            f"Use DUKE Highway as alternative for Kepong–City trips."
        )

    if any(w in q for w in ["clear","free","fast","best road"]):
        if clear_names:
            return f"🟢 Currently clear roads: **{', '.join(clear_names)}**. These are your best options right now."
        return "🟡 No fully clear major roads at the moment — ELITE and MEX are the least congested options."

    if any(w in q for w in ["worst","avoid","bad","jam","congested"]):
        bad = severe_names + heavy_names[:2]
        if bad:
            return f"🔴 Worst roads right now: **{', '.join(bad)}**. Avoid these if possible."
        return "🟢 No severe jams at this time — lucky you!"

    # Default
    return (
        f"🤖 Based on live data: avg KL speed is **{avg_speed} km/h** "
        f"({'peak hour' if is_peak else 'off-peak'}). "
        f"{'Severe: ' + ', '.join(severe_names) + '. ' if severe_names else ''}"
        f"{'Clear: ' + ', '.join(clear_names[:2]) + '.' if clear_names else ''} "
        f"Rain probability: {rain_prob}%. Ask me about a specific road or route for details!"
    )
