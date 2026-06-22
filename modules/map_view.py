"""
modules/map_view.py
-------------------
Interactive Folium map with TomTom vector tile layer option.
Uses CartoDB Dark as base (no key required) + TomTom traffic tiles when key present.
TomTom tile URL: https://api.tomtom.com/traffic/map/4/tile/flow/relative/{z}/{x}/{y}.png?key=...
"""

import folium
from folium import plugins

KL_CENTER    = [3.1390, 101.6869]
DEFAULT_ZOOM = 12

STATUS_COLOR  = {"SEVERE":"#ff4444","HEAVY":"#ff6b35","MODERATE":"#ffcc00","CLEAR":"#00e676"}
STATUS_WEIGHT = {"SEVERE":7,"HEAVY":6,"MODERATE":5,"CLEAR":4}

INCIDENT_ICONS = {
    "ACCIDENT":   ("🚨","#ff4444"),
    "ROAD_WORKS": ("🚧","#ff6b35"),
    "FLOOD":      ("🌊","#4488ff"),
    "JAR":        ("⚠️","#ffcc00"),
}

CHECKPOINTS = {
    "Petaling Jaya": (3.1073,101.6067),
    "KLCC":          (3.1579,101.7119),
    "Shah Alam":     (3.0738,101.5183),
    "Subang Jaya":   (3.0565,101.5851),
    "Puchong":       (3.0215,101.6186),
    "Cheras":        (3.0906,101.7496),
}


def build_map(traffic_data: dict, route_data: dict | None,
              show_incidents: bool, show_heatmap: bool,
              tomtom_key: str = "") -> folium.Map:

    m = folium.Map(location=KL_CENTER, zoom_start=DEFAULT_ZOOM,
                   tiles=None, prefer_canvas=True)

    # ── Base tile layer (always available) ───────────────────────────────────
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="&copy; CARTO",
        name="Dark Base Map",
        max_zoom=19,
    ).add_to(m)

    # ── TomTom live traffic flow tile overlay (when key present) ─────────────
    if tomtom_key:
        folium.TileLayer(
            tiles=(
                f"https://api.tomtom.com/traffic/map/4/tile/flow/relative/"
                "{z}/{x}/{y}.png?key=" + tomtom_key
            ),
            attr="&copy; TomTom",
            name="TomTom Live Traffic",
            max_zoom=18,
            opacity=0.65,
        ).add_to(m)

    # ── Road condition overlays ──────────────────────────────────────────────
    road_layer = folium.FeatureGroup(name="Road Conditions")
    live_roads = {r["name"]: r for r in traffic_data.get("roads", [])}

    for road in traffic_data.get("roads", []):
        waypoints = road.get("waypoints", [])
        if len(waypoints) < 2:
            continue
        status = road.get("status", "MODERATE")
        color  = STATUS_COLOR.get(status, "#5a7a8a")
        weight = STATUS_WEIGHT.get(status, 4)
        speed  = road.get("speed_kmh", "–")

        # Glow
        folium.PolyLine(waypoints, color=color, weight=weight+8, opacity=0.12).add_to(road_layer)
        # Road line
        folium.PolyLine(
            waypoints, color=color, weight=weight, opacity=0.88,
            tooltip=f"{road['name']} · {status} · {speed} km/h",
        ).add_to(road_layer)

    road_layer.add_to(m)

    # ── Heatmap ──────────────────────────────────────────────────────────────
    if show_heatmap:
        heat_pts = []
        for road in traffic_data.get("roads", []):
            cong  = road.get("congestion_pct", 50) / 100
            for wp in road.get("waypoints", []):
                heat_pts.append([wp[0], wp[1], cong])
        if heat_pts:
            plugins.HeatMap(
                heat_pts, name="Congestion Heatmap",
                min_opacity=0.2, radius=28, blur=22,
                gradient={0.3:"#00e676",0.6:"#ffcc00",0.8:"#ff6b35",1.0:"#ff4444"},
            ).add_to(m)

    # ── Incident markers ─────────────────────────────────────────────────────
    if show_incidents:
        inc_layer = folium.FeatureGroup(name="Incidents")
        for inc in traffic_data.get("incidents", []):
            coords = inc.get("coords")
            if not coords:
                continue
            icon_char, color = INCIDENT_ICONS.get(inc.get("type","JAR"), ("⚠️","#ffcc00"))
            folium.Marker(
                location=coords,
                tooltip=f"{icon_char} {inc['title']} — {inc['location']}",
                popup=folium.Popup(
                    f"<b>{inc['title']}</b><br>{inc['location']}", max_width=220),
                icon=folium.DivIcon(
                    html=f'<div style="background:{color}22;border:2px solid {color};'
                         f'border-radius:50%;width:28px;height:28px;display:flex;'
                         f'align-items:center;justify-content:center;font-size:14px;'
                         f'box-shadow:0 0 8px {color}88;">{icon_char}</div>',
                    icon_size=(28,28), icon_anchor=(14,14),
                ),
            ).add_to(inc_layer)
        inc_layer.add_to(m)

    # ── Landmark dots ────────────────────────────────────────────────────────
    cp_layer = folium.FeatureGroup(name="Landmarks")
    for name, (lat, lng) in CHECKPOINTS.items():
        folium.CircleMarker(
            location=[lat,lng], radius=5,
            color="#00e5ff", fill=True, fill_color="#00e5ff",
            fill_opacity=0.7, tooltip=name,
        ).add_to(cp_layer)
    cp_layer.add_to(m)

    # ── Route polyline ───────────────────────────────────────────────────────
    if route_data and route_data.get("status") == "OK":
        poly = route_data.get("polyline")
        if poly and len(poly) >= 2:
            route_layer = folium.FeatureGroup(name="Your Route")
            folium.PolyLine(poly, color="#00e5ff", weight=14, opacity=0.12).add_to(route_layer)
            folium.PolyLine(
                poly, color="#00e5ff", weight=5, opacity=0.9,
                tooltip=f"Route: {route_data.get('duration_text','–')} · {route_data.get('distance_text','–')}",
            ).add_to(route_layer)

            # Start marker
            sc = route_data.get("start_coords")
            ec = route_data.get("end_coords")
            if sc:
                folium.Marker(sc, tooltip=route_data.get("origin_label","Start"),
                    icon=folium.DivIcon(
                        html='<div style="background:#00e676;border-radius:50%;width:14px;height:14px;border:2px solid white;box-shadow:0 0 8px #00e676"></div>',
                        icon_size=(14,14), icon_anchor=(7,7))).add_to(route_layer)
            if ec:
                folium.Marker(ec, tooltip=route_data.get("dest_label","Destination"),
                    icon=folium.DivIcon(
                        html='<div style="background:#ff4444;border-radius:50%;width:14px;height:14px;border:2px solid white;box-shadow:0 0 8px #ff4444"></div>',
                        icon_size=(14,14), icon_anchor=(7,7))).add_to(route_layer)
            route_layer.add_to(m)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    # ── Legend ───────────────────────────────────────────────────────────────
    legend = """
    <div style="position:fixed;bottom:20px;left:20px;z-index:1000;
    background:rgba(8,12,16,0.92);border:1px solid #1e2d3a;border-radius:6px;
    padding:12px 16px;font-family:'Courier New',monospace;font-size:11px;color:#e8f4f8;">
    <b style="color:#00e5ff;letter-spacing:.1em">TRAFFIC FLOW</b><br><br>
    <span style="color:#ff4444">━━</span> Severe &lt;20 km/h<br>
    <span style="color:#ff6b35">━━</span> Heavy 20–40 km/h<br>
    <span style="color:#ffcc00">━━</span> Moderate 40–65 km/h<br>
    <span style="color:#00e676">━━</span> Clear &gt;65 km/h<br>
    <span style="color:#00e5ff">━━</span> Your route
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))

    return m
