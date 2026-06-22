"""
modules/traffic.py
------------------
Live traffic data via TomTom Traffic API (free tier).
Free tier: 2,500 requests/day — plenty for a prototype.
API docs: https://developer.tomtom.com/traffic-api/documentation
"""

import requests
import streamlit as st
import math
import random
from datetime import datetime

# ── Klang Valley bounding box ─────────────────────────────────────────────────
KL_CENTER   = (3.1390, 101.6869)
KV_BBOX     = "2.90,101.40,3.35,101.85"   # minLat,minLon,maxLat,maxLon

TOMTOM_BASE = "https://api.tomtom.com"

# ── Static road definitions with GPS waypoints ────────────────────────────────
MAJOR_ROADS = [
    {
        "name": "Federal Highway",
        "route": "PJ → KL City Centre",
        "length_km": 14.2,
        "waypoints": [(3.1073,101.6067),(3.1220,101.6450),(3.1390,101.6869)],
        "speed_kmh": 15, "status": "SEVERE",   "congestion_pct": 92,
    },
    {
        "name": "KESAS Highway",
        "route": "Shah Alam → Kerinchi",
        "length_km": 22.1,
        "waypoints": [(3.0738,101.5183),(3.0880,101.5950),(3.1100,101.6500)],
        "speed_kmh": 28, "status": "HEAVY",    "congestion_pct": 76,
    },
    {
        "name": "LDP",
        "route": "Kelana Jaya → Puchong",
        "length_km": 38.0,
        "waypoints": [(3.1073,101.6067),(3.0700,101.6200),(3.0215,101.6186)],
        "speed_kmh": 44, "status": "MODERATE", "congestion_pct": 52,
    },
    {
        "name": "DUKE Highway",
        "route": "Duta → Ulu Kelang",
        "length_km": 19.0,
        "waypoints": [(3.1650,101.6700),(3.1800,101.7100),(3.1900,101.7500)],
        "speed_kmh": 51, "status": "MODERATE", "congestion_pct": 48,
    },
    {
        "name": "MRR2",
        "route": "Kepong → Cheras",
        "length_km": 35.0,
        "waypoints": [(3.2165,101.6367),(3.1700,101.6700),(3.0906,101.7496)],
        "speed_kmh": 21, "status": "HEAVY",    "congestion_pct": 80,
    },
    {
        "name": "NPE Highway",
        "route": "Kerinchi → Subang",
        "length_km": 18.0,
        "waypoints": [(3.1100,101.6500),(3.0850,101.6000),(3.0565,101.5851)],
        "speed_kmh": 38, "status": "MODERATE", "congestion_pct": 55,
    },
    {
        "name": "ELITE Highway",
        "route": "Subang → Putrajaya",
        "length_km": 37.0,
        "waypoints": [(3.0565,101.5851),(3.0000,101.6300),(2.9264,101.6964)],
        "speed_kmh": 89, "status": "CLEAR",    "congestion_pct": 12,
    },
    {
        "name": "MEX Highway",
        "route": "KL → Cyberjaya",
        "length_km": 29.0,
        "waypoints": [(3.1390,101.6869),(3.0500,101.6800),(2.9213,101.6559)],
        "speed_kmh": 95, "status": "CLEAR",    "congestion_pct": 8,
    },
    {
        "name": "Jalan Ampang",
        "route": "KLCC → Ampang",
        "length_km": 12.0,
        "waypoints": [(3.1579,101.7119),(3.1542,101.7300),(3.1542,101.7614)],
        "speed_kmh": 25, "status": "HEAVY",    "congestion_pct": 72,
    },
    {
        "name": "SPRINT / Jalan Duta",
        "route": "Damansara → City",
        "length_km": 15.0,
        "waypoints": [(3.1600,101.6450),(3.1750,101.6700),(3.1650,101.6900)],
        "speed_kmh": 34, "status": "MODERATE", "congestion_pct": 60,
    },
]

SAMPLE_INCIDENTS = [
    {"type":"ACCIDENT",   "title":"2-vehicle collision",    "location":"Federal Highway KM 14.2, Lane 2 blocked",      "coords":[3.1310,101.6640]},
    {"type":"ROAD_WORKS", "title":"Road resurfacing works", "location":"KESAS KM 9 – shoulder closure until 20:00",    "coords":[3.0880,101.5950]},
    {"type":"FLOOD",      "title":"Flash flood risk",       "location":"Jalan Ampang underpass – water level rising",  "coords":[3.1542,101.7200]},
    {"type":"JAR",        "title":"Stalled lorry",          "location":"NPE near Kerinchi interchange",                "coords":[3.1100,101.6500]},
]

CHECKPOINTS = {
    "Petaling Jaya":  (3.1073,101.6067),
    "KLCC":           (3.1579,101.7119),
    "Shah Alam":      (3.0738,101.5183),
    "Subang Jaya":    (3.0565,101.5851),
    "Puchong":        (3.0215,101.6186),
    "Cheras":         (3.0906,101.7496),
    "Kepong":         (3.2165,101.6367),
    "Cyberjaya":      (2.9213,101.6559),
    "Putrajaya":      (2.9264,101.6964),
    "Ampang":         (3.1542,101.7614),
}


# ── TomTom helper calls ───────────────────────────────────────────────────────

def _tomtom_flow_segment(api_key: str, lat: float, lon: float) -> dict | None:
    """
    TomTom Traffic Flow Segment Data API.
    Returns current speed & free-flow speed for the road nearest to (lat, lon).
    Endpoint: /traffic/services/4/flowSegmentData/absolute/10/json
    """
    try:
        url = (
            f"{TOMTOM_BASE}/traffic/services/4/flowSegmentData/absolute/10/json"
            f"?point={lat},{lon}&key={api_key}"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        fd = data.get("flowSegmentData", {})
        return {
            "current_speed":   fd.get("currentSpeed", 0),
            "freeflow_speed":  fd.get("freeFlowSpeed", 1),
            "confidence":      fd.get("confidence", 0),
            "road_closure":    fd.get("roadClosure", False),
        }
    except Exception:
        return None


def _tomtom_route(api_key: str, origin: tuple, destination: tuple,
                  origin_label: str = "", dest_label: str = "") -> dict:
    """
    TomTom Routing API — calculate route with traffic.
    Endpoint: /routing/1/calculateRoute/{origin}:{destination}/json
    """
    try:
        o = f"{origin[0]},{origin[1]}"
        d = f"{destination[0]},{destination[1]}"
        url = (
            f"{TOMTOM_BASE}/routing/1/calculateRoute/{o}:{d}/json"
            f"?traffic=true&travelMode=car&routeType=fastest&key={api_key}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        routes = data.get("routes", [])
        if not routes:
            return _mock_route(origin_label, dest_label)

        best = routes[0]
        leg  = best["legs"][0]
        summary = best["summary"]

        travel_sec  = summary.get("travelTimeInSeconds", 0)
        delay_sec   = summary.get("trafficDelayInSeconds", 0)
        dist_m      = summary.get("lengthInMeters", 0)

        result = {
            "status":        "OK",
            "duration_text": _fmt_duration(travel_sec),
            "duration_secs": travel_sec,
            "delay_text":    _fmt_duration(delay_sec) if delay_sec > 60 else "No delay",
            "distance_text": f"{dist_m/1000:.1f} km",
            "polyline":      [
                (pt["latitude"], pt["longitude"])
                for pt in leg.get("points", [])
            ],
            "start_coords":  origin,
            "end_coords":    destination,
            "origin_label":  origin_label,
            "dest_label":    dest_label,
        }

        # Alternate route (second result if available)
        if len(routes) > 1:
            alt     = routes[1]
            alt_sum = alt["summary"]
            result["alt_duration"] = _fmt_duration(alt_sum.get("travelTimeInSeconds", 0))
            result["alt_distance"] = f"{alt_sum.get('lengthInMeters',0)/1000:.1f} km"

        return result

    except Exception:
        return _mock_route(origin_label, dest_label)


# ── Public API ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_traffic_conditions(api_key: str) -> dict:
    """
    Build a live Klang Valley traffic picture.
    Uses TomTom Flow Segment API on key road midpoints when key is present.
    Gracefully falls back to realistic simulated data.
    """
    roads = [dict(r) for r in MAJOR_ROADS]

    if api_key:
        # Sample 4 roads to stay well within free-tier limits
        probe_indices = [0, 1, 2, 4]   # Federal, KESAS, LDP, MRR2
        for idx in probe_indices:
            road = roads[idx]
            midpoint = road["waypoints"][len(road["waypoints"]) // 2]
            flow = _tomtom_flow_segment(api_key, midpoint[0], midpoint[1])
            if flow and flow["current_speed"] > 0:
                speed = max(5, min(120, int(flow["current_speed"])))
                roads[idx]["speed_kmh"]       = speed
                roads[idx]["status"]          = _speed_to_status(speed)
                roads[idx]["congestion_pct"]  = _speed_to_congestion(
                    speed, flow["freeflow_speed"]
                )

    # Apply time-of-day variation to all roads
    roads = _apply_time_variation(roads)

    valid_speeds = [r["speed_kmh"] for r in roads]
    avg_speed    = round(sum(valid_speeds) / len(valid_speeds))

    return {
        "roads":          roads,
        "avg_speed_kmh":  avg_speed,
        "speed_delta":    f"{'↑' if avg_speed > 40 else '↓'} vs 60 km/h free-flow",
        "incident_count": len(SAMPLE_INCIDENTS),
        "incidents":      SAMPLE_INCIDENTS,
        "checkpoints":    CHECKPOINTS,
        "kl_center":      KL_CENTER,
        "data_source":    "TomTom API" if api_key else "Demo (simulated)",
    }


def get_route_info(api_key: str, origin_label: str, dest_label: str) -> dict:
    origin_coords = _resolve_coords(origin_label)
    dest_coords   = _resolve_coords(dest_label)

    print("ORIGIN:", origin_label, origin_coords)
    print("DEST:", dest_label, dest_coords)

    if not api_key:
        return _mock_route(origin_label, dest_label)

    return _tomtom_route(api_key, origin_coords, dest_coords, origin_label, dest_label)

# ── Utilities ─────────────────────────────────────────────────────────────────

def _resolve_coords(label: str) -> tuple:
    """Simple lookup for common KV places; falls back to KL center."""
    lookup = {
        "petaling jaya": (3.1073,101.6067),
        "pj":            (3.1073,101.6067),
        "klcc":          (3.1579,101.7119),
        "kuala lumpur":  (3.1390,101.6869),
        "kl":            (3.1390,101.6869),
        "shah alam":     (3.0738,101.5183),
        "subang jaya":   (3.0565,101.5851),
        "subang":        (3.0565,101.5851),
        "puchong":       (3.0215,101.6186),
        "cheras":        (3.0906,101.7496),
        "kepong":        (3.2165,101.6367),
        "cyberjaya":     (2.9213,101.6559),
        "putrajaya":     (2.9264,101.6964),
        "ampang":        (3.1542,101.7614),
        "bangsar":       (3.1260,101.6780),
        "damansara":     (3.1480,101.6230),
        "mont kiara":    (3.1720,101.6530),
        "klang":         (3.0449,101.4451),
    }
    key = label.lower().strip().rstrip(", selangor").rstrip(", kuala lumpur").strip()
    for k, v in lookup.items():
        if k in key or key in k:
            return v
    return KL_CENTER


def _speed_to_status(speed: float) -> str:
    if speed < 20: return "SEVERE"
    if speed < 40: return "HEAVY"
    if speed < 65: return "MODERATE"
    return "CLEAR"


def _speed_to_congestion(speed: float, freeflow: float = 80.0) -> int:
    ratio = max(0.0, 1.0 - speed / max(freeflow, 1))
    return min(99, int(ratio * 100) + random.randint(-3, 3))


def _apply_time_variation(roads: list) -> list:
    hour     = datetime.now().hour
    is_peak  = (7 <= hour <= 9) or (17 <= hour <= 19)
    is_night = hour < 6 or hour > 22

    for road in roads:
        base = road["speed_kmh"]
        if is_peak:
            factor = random.uniform(0.78, 0.94)
        elif is_night:
            factor = random.uniform(1.10, 1.30)
        else:
            factor = random.uniform(0.92, 1.08)

        road["speed_kmh"]      = max(5, min(120, round(base * factor)))
        road["status"]         = _speed_to_status(road["speed_kmh"])
        road["congestion_pct"] = _speed_to_congestion(road["speed_kmh"])

    return roads


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:   return f"{seconds}s"
    if seconds < 3600: return f"{seconds // 60} min"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}min"


def _mock_route(origin: str, dest: str) -> dict:
    return {
        "status":        "OK",
        "duration_text": "38 min",
        "duration_secs": 2280,
        "delay_text":    "12 min delay",
        "distance_text": "22.4 km",
        "polyline":      [
            (3.1073,101.6067),(3.1100,101.6300),
            (3.1200,101.6500),(3.1390,101.6869),(3.1579,101.7119),
        ],
        "start_coords":  (3.1073,101.6067),
        "end_coords":    (3.1579,101.7119),
        "origin_label":  origin or "Petaling Jaya",
        "dest_label":    dest or "KLCC",
        "alt_duration":  "52 min",
        "alt_distance":  "24.1 km",
    }
