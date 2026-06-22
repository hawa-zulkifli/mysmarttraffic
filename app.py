"""
MY SMART TRAFFIC — Klang Valley Traffic Intelligence
Streamlit app · TomTom API · HuggingFace flan-t5 · OpenWeatherMap
"""

import streamlit as st
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="MY SMART TRAFFIC · Klang Valley Traffic",
    page_icon="🚦",
    layout="wide",
)

def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)


# ── Secrets helper ────────────────────────────────────────────────────────────
def get_secret(key, default=""):
    try:    return st.secrets[key]
    except: return os.getenv(key, default)

TOMTOM_KEY      = get_secret("TOMTOM_API_KEY")
OPENWEATHER_KEY = get_secret("OPENWEATHER_API_KEY")
HF_API_KEY      = get_secret("HF_API_KEY")   # HuggingFace token

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.stApp { background: #080c10; }
#MainMenu, footer, header {
    visibility: visible !important;
}
header {
    visibility: visible !important;
}
.main-header {
    background: linear-gradient(135deg,#0e1318,#141b22);
    border:1px solid #1e2d3a; border-radius:8px;
    padding:18px 28px; margin-bottom:18px;
    display:flex; align-items:center; justify-content:space-between;
}
.logo-text { font-size:45px;font-weight:800;color:#00e5ff;letter-spacing:.1em;
    text-shadow:0 0 20px rgba(0,229,255,.4);margin:0; }
.tagline { font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a7a8a;
    letter-spacing:.08em;margin:4px 0 0; }

.ai-box {
    background:linear-gradient(135deg,rgba(0,229,255,.04),#0e1318);
    border:1px solid #1e2d3a;border-left:3px solid #00e5ff;
    border-radius:6px;padding:16px 18px;font-size:13px;line-height:1.75;color:#e8f4f8;
}
.section-head {
    font-family:'JetBrains Mono',monospace;font-size:9px;color:#5a7a8a;
    text-transform:uppercase;letter-spacing:.15em;
    border-bottom:1px solid #1e2d3a;padding-bottom:6px;margin-bottom:12px;
}
.incident-item {
    background:#0e1318;border:1px solid #1e2d3a;border-radius:6px;
    padding:11px 14px;margin-bottom:8px;font-size:12px;
}
/* ── SIDEBAR TOGGLE — always visible ── */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: fixed !important;
    left: 0px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    z-index: 99999 !important;
    background: #00e5ff !important;
    width: 20px !important;
    height: 56px !important;
    border-radius: 0 8px 8px 0 !important;
    cursor: pointer !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    fill: #080c10 !important;
    color: #080c10 !important;
}
[data-testid="stSidebar"] {
    background: #0a0f14 !important;
    border-right: 1px solid #1e2d3a !important;
    display: block !important;
}
.stTextInput>div>div>input { background:#141b22 !important;border:1px solid #1e2d3a !important;color:#e8f4f8 !important; }
.stButton>button {
    background:rgba(0,229,255,.1) !important;border:1px solid rgba(0,229,255,.3) !important;
    color:#00e5ff !important;border-radius:4px !important;font-family:'Syne',sans-serif !important;
    font-weight:600 !important;letter-spacing:.04em !important;
}
.stButton>button:hover { background:rgba(0,229,255,.2) !important;box-shadow:0 0 15px rgba(0,229,255,.2) !important; }
.stTabs [data-baseweb="tab-list"] { background:#0e1318;border-bottom:1px solid #1e2d3a; }
.stTabs [data-baseweb="tab"] { color:#5a7a8a;font-size:12px;font-weight:600;letter-spacing:.04em; }
.stTabs [aria-selected="true"] { color:#00e5ff !important;border-bottom:2px solid #00e5ff !important; }
[data-testid="stMetric"] { background:#0e1318;border:1px solid #1e2d3a;border-radius:6px;padding:12px 16px; }
hr { border-color:#1e2d3a !important; }
#MainMenu,footer,header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Imports ───────────────────────────────────────────────────────────────────
from modules.weather   import get_weather
from modules.traffic   import get_traffic_conditions, get_route_info, MAJOR_ROADS
from modules.ai_engine import get_ai_analysis, ask_traffic_assistant
from modules.map_view  import build_map
from streamlit_folium  import st_folium

# ── Header ────────────────────────────────────────────────────────────────────
now_str  = datetime.now().strftime("%a %d %b · %H:%M")
is_peak  = 7 <= datetime.now().hour <= 9 or 17 <= datetime.now().hour <= 19

# API status badges
badges = []
if TOMTOM_KEY:      badges.append(('<span style="color:#00e676;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.3);padding:3px 10px;border-radius:2px;font-size:10px">● TOMTOM LIVE</span>', True))
else:               badges.append(('<span style="color:#5a7a8a;background:rgba(90,122,138,.1);border:1px solid #1e2d3a;padding:3px 10px;border-radius:2px;font-size:10px">TOMTOM DEMO</span>', False))
if HF_API_KEY:      badges.append(('<span style="color:#00e5ff;background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.3);padding:3px 10px;border-radius:2px;font-size:10px">● HF AI ACTIVE</span>', True))
else:               badges.append(('<span style="color:#ffcc00;background:rgba(255,204,0,.1);border:1px solid rgba(255,204,0,.3);padding:3px 10px;border-radius:2px;font-size:10px">AI RULE-BASED</span>', False))
if OPENWEATHER_KEY: badges.append(('<span style="color:#00e676;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.3);padding:3px 10px;border-radius:2px;font-size:10px">● WEATHER LIVE</span>', True))

badge_html = "&nbsp;".join(b[0] for b in badges)

st.markdown(f"""
<div class="main-header">
  <div>
    <p class="logo-text">● MY SMART TRAFFIC</p>
    <p class="tagline">KLANG VALLEY TRAFFIC INTELLIGENCE · {now_str} · {"⚠ PEAK HOUR" if is_peak else "● LIVE"}</p>
  </div>
  <div style="font-family:'JetBrains Mono',monospace">{badge_html}</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="section-head">🗺 Route Planner</p>', unsafe_allow_html=True)
    origin      = st.text_input("From", value="Petaling Jaya")
    destination = st.text_input("To",   value="KLCC")
    if st.button("🔍 Plan Route + AI Analysis", width='stretch'):
        st.session_state["route_requested"] = True

    st.markdown("---")
    st.markdown('<p class="section-head">⚙ Map Options</p>', unsafe_allow_html=True)
    show_incidents = st.toggle("Show Incidents",     value=True)
    show_heatmap   = st.toggle("Congestion Heatmap", value=True)
    auto_refresh   = st.toggle("Auto-Refresh (60s)", value=False)

    if auto_refresh:
        st.cache_data.clear()

    st.markdown("---")
    st.markdown('<p class="section-head">📡 Data Sources</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a7a8a;line-height:2.2">
    ● TomTom Traffic API (free tier)<br>
    ● OpenWeatherMap API (free tier)<br>
    ● HuggingFace flan-t5-large<br>
    ● Rule-based KV traffic engine
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p class="section-head">ℹ API Key Status</p>', unsafe_allow_html=True)
    for label, active in [("TomTom", bool(TOMTOM_KEY)), ("OpenWeather", bool(OPENWEATHER_KEY)), ("HuggingFace", bool(HF_API_KEY))]:
        dot   = "🟢" if active else "🔴"
        state = "Connected" if active else "Not set (demo)"
        st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#5a7a8a">{dot} {label}: {state}</div>', unsafe_allow_html=True)

# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner("Loading live traffic & weather..."):
    weather_data = get_weather(OPENWEATHER_KEY)
    traffic_data = get_traffic_conditions(TOMTOM_KEY)

# ── Metrics row ───────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
avg_speed  = traffic_data.get("avg_speed_kmh", "–")
temp       = weather_data.get("temp_c", "–")
rain_prob  = weather_data.get("rain_prob_pct", "–")
incidents  = traffic_data.get("incident_count", "–")

with m1: st.metric("🚗 KL Avg Speed",    f"{avg_speed} km/h",  traffic_data.get("speed_delta",""))
with m2: st.metric("🌡 Temperature",     f"{temp}°C",          weather_data.get("feels_like_delta",""))
with m3: st.metric("🌧 Rain Probability",f"{rain_prob}%",      "⚠ High" if isinstance(rain_prob,(int,float)) and rain_prob>60 else "Low",
                   delta_color="inverse" if isinstance(rain_prob,(int,float)) and rain_prob>60 else "normal")
with m4: st.metric("🚨 Incidents",       str(incidents),       "⚠ Active" if isinstance(incidents,int) and incidents>0 else "Clear")
with m5: st.metric("🕐 Peak Status",     "PEAK HOUR" if is_peak else "Off-Peak",
                   "+15–30 min" if is_peak else "Normal",
                   delta_color="inverse" if is_peak else "normal")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_map, tab_roads, tab_ai, tab_chat = st.tabs([
    "🗺  Live Map", "🛣  Road Status", "🤖  AI Analysis", "💬  Assistant"
])

# ════════════════════════════════════════════════════════
# TAB 1 — MAP
# ════════════════════════════════════════════════════════
with tab_map:
    col_map, col_side = st.columns([3, 1])

    with col_map:
        route_data = None
        if st.session_state.get("route_requested"):
            with st.spinner("Fetching route from TomTom..."):
                route_data = get_route_info(TOMTOM_KEY, origin, destination)

        traffic_map = build_map(traffic_data, route_data, show_incidents, show_heatmap, TOMTOM_KEY)
        st_folium(traffic_map, height=520, width='stretch')

        if route_data and route_data.get("status") == "OK":
            delay_color = "#ff4444" if "min" in route_data.get("delay_text","") and "No" not in route_data.get("delay_text","") else "#00e676"
            st.markdown(f"""
            <div style="background:#0e1318;border:1px solid #1e2d3a;border-top:3px solid #00e5ff;
            border-radius:6px;padding:14px 18px;margin-top:10px;">
              <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#5a7a8a;
              letter-spacing:.1em;margin-bottom:8px;">TOMTOM ROUTE RESULT</div>
              <span style="font-size:22px;font-weight:800;color:#00e5ff">{route_data.get('duration_text','–')}</span>
              <span style="font-size:12px;color:#5a7a8a;margin-left:8px">{route_data.get('distance_text','')}</span>
              &nbsp;&nbsp;
              <span style="font-size:11px;color:{delay_color};font-family:'JetBrains Mono',monospace">
                ⏱ {route_data.get('delay_text','')}</span><br>
              <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a7a8a;margin-top:6px">
                📍 {route_data.get('origin_label',origin)} → {route_data.get('dest_label',destination)}
              </div>
              {"<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#5a7a8a;margin-top:4px'>Alt: " + route_data.get('alt_duration','–') + " · " + route_data.get('alt_distance','–') + "</div>" if route_data.get('alt_duration') else ""}
            </div>
            """, unsafe_allow_html=True)

    with col_side:
        st.markdown('<p class="section-head">☁ Weather · KL</p>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#0e1318;border:1px solid #1e2d3a;border-radius:6px;padding:14px 16px;margin-bottom:12px">
          <div style="font-size:36px">{weather_data.get('icon','🌤')}</div>
          <div style="font-size:30px;font-weight:800;color:#e8f4f8;line-height:1">{temp}°C</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a7a8a;margin:4px 0">
            {weather_data.get('description','–').title()}</div>
          <hr>
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a7a8a;line-height:2">
            💧 {weather_data.get('humidity','–')}% humidity<br>
            🌬 {weather_data.get('wind_kmh','–')} km/h wind<br>
            👁 {weather_data.get('visibility_km','–')} km visibility<br>
            🌧 <b style="color:{'#ffcc00' if isinstance(rain_prob,(int,float)) and rain_prob>60 else '#00e676'}">{rain_prob}%</b> rain
          </div>
        </div>
        """, unsafe_allow_html=True)

        if isinstance(rain_prob,(int,float)) and rain_prob > 55:
            st.warning(f"⚡ Rain likely. Expect +10–20 min delays on low-lying roads.")

        st.markdown('<p class="section-head">🚨 Incidents</p>', unsafe_allow_html=True)
        for inc in traffic_data.get("incidents",[])[:4]:
            icons = {"ACCIDENT":"🚨","ROAD_WORKS":"🚧","FLOOD":"🌊","JAR":"⚠️"}
            st.markdown(f"""
            <div class="incident-item">
              {icons.get(inc.get('type','JAR'),'⚠️')} <b>{inc.get('title','')}</b><br>
              <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a7a8a">
                {inc.get('location','')}</span>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# TAB 2 — ROAD STATUS
# ════════════════════════════════════════════════════════
with tab_roads:
    src = traffic_data.get("data_source","")
    st.markdown(f'<p class="section-head">🛣 Major KV Corridors · Source: {src}</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    for i, road in enumerate(traffic_data.get("roads", MAJOR_ROADS)):
        status  = road.get("status","MODERATE")
        speed   = road.get("speed_kmh","–")
        cong    = road.get("congestion_pct",50)
        color_map = {"SEVERE":"#ff4444","HEAVY":"#ff6b35","MODERATE":"#ffcc00","CLEAR":"#00e676"}
        c = color_map.get(status,"#5a7a8a")
        # Safely convert hex to RGB for rgba()
        try:
            r_int = int(c[1:3],16); g_int = int(c[3:5],16); b_int = int(c[5:7],16)
            bg = f"rgba({r_int},{g_int},{b_int},0.08)"
        except Exception:
            bg = "rgba(90,122,138,0.08)"

        col = col_a if i % 2 == 0 else col_b
        with col:
            st.markdown(f"""
            <div style="background:#0e1318;border:1px solid #1e2d3a;border-left:3px solid {c};
            border-radius:6px;padding:14px 16px;margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between">
                <div>
                  <div style="font-size:14px;font-weight:700;color:#e8f4f8">{road['name']}</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a7a8a;margin-top:2px">{road.get('route','')}</div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:10px;font-weight:700;padding:3px 10px;border-radius:2px;
                  background:{bg};color:{c};border:1px solid {c}44">{status}</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                  color:{c};margin-top:4px;font-weight:600">{speed} km/h</div>
                </div>
              </div>
              <div style="margin-top:10px;height:4px;background:#1e2d3a;border-radius:2px;overflow:hidden">
                <div style="height:100%;width:{cong}%;background:{c};border-radius:2px"></div>
              </div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#5a7a8a;margin-top:4px">
                {cong}% congested · {road.get('length_km','–')} km
              </div>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# TAB 3 — AI ANALYSIS
# ════════════════════════════════════════════════════════
with tab_ai:
    col_l, col_r = st.columns([3, 2])

    with col_l:
        model_label = "google/flan-t5-large (HuggingFace)" if HF_API_KEY else "Rule-based engine (no HF key)"
        st.markdown(f'<p class="section-head">🤖 AI Traffic Analysis · {model_label}</p>', unsafe_allow_html=True)

        if not HF_API_KEY:
            st.info("💡 Add your free **HF_API_KEY** (HuggingFace token) in secrets to enable flan-t5 ML inference. Running rule-based analysis now.")

        if st.button("🔄 Refresh Analysis", width='stretch'):
            st.cache_data.clear()

        with st.spinner("Generating analysis..."):
            ai_text = get_ai_analysis(HF_API_KEY, traffic_data, weather_data)

        if ai_text:
            st.markdown(f'<div class="ai-box">{ai_text}</div>', unsafe_allow_html=True)
        else:
            st.error("Analysis failed.")

    with col_r:
        st.markdown('<p class="section-head">📈 Congestion Forecast · Today</p>', unsafe_allow_html=True)
        import pandas as pd, altair as alt

        hours  = [f"{h:02d}:00" for h in range(7,22)]
        levels = [65,85,70,45,40,38,42,50,55,90,95,88,70,55,40]
        ch     = datetime.now().hour
        df = pd.DataFrame({"Hour":hours,"Congestion":levels,
                           "Now":[h.startswith(f"{ch:02d}") for h in hours]})

        def bar_color(row):
            if row["Now"]: return "#00e5ff"
            if row["Congestion"] > 75: return "#ff4444"
            if row["Congestion"] > 55: return "#ffcc00"
            return "#00e676"
        df["Color"] = df.apply(bar_color, axis=1)

        chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=alt.X("Hour:N", axis=alt.Axis(labelColor="#5a7a8a", labelFontSize=9,
                                             gridColor="#1e2d3a", tickColor="#1e2d3a")),
            y=alt.Y("Congestion:Q", axis=alt.Axis(labelColor="#5a7a8a", gridColor="#1e2d3a"),
                    scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("Color:N", scale=None),
            tooltip=["Hour", "Congestion"]
        ).properties(height=220, background="#0e1318").configure_view(
            stroke="#1e2d3a"
        ).configure_axis(domainColor="#1e2d3a")
        st.altair_chart(chart, use_container_width=True)

        st.markdown("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a7a8a;
        line-height:1.9;background:#0e1318;border:1px solid #1e2d3a;border-radius:4px;padding:10px 12px">
        <span style="color:#00e5ff">■</span> Now &nbsp;
        <span style="color:#ff4444">■</span> Heavy &nbsp;
        <span style="color:#ffcc00">■</span> Moderate &nbsp;
        <span style="color:#00e676">■</span> Clear<br>
        <span style="color:#5a7a8a">Pattern based on historical KV traffic data</span>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# TAB 4 — CHAT ASSISTANT
# ════════════════════════════════════════════════════════
with tab_chat:
    st.markdown(f'<p class="section-head">💬 Traffic Assistant · {"flan-t5-large" if HF_API_KEY else "Rule-based engine"}</p>', unsafe_allow_html=True)

    if not HF_API_KEY:
        st.info("Running keyword-based assistant. Add **HF_API_KEY** (free at huggingface.co) for AI-powered replies.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render chat history
    for msg in st.session_state.chat_history:
        role_color = "#141b22" if msg["role"] == "user" else "rgba(0,229,255,0.04)"
        border_col = "#1e2d3a" if msg["role"] == "user" else "rgba(0,229,255,0.2)"
        icon = "👤" if msg["role"] == "user" else "🤖"
        align = "left" if msg["role"] == "user" else "right"
        st.markdown(f"""
        <div style="background:{role_color};border:1px solid {border_col};border-radius:6px;
        padding:10px 14px;font-size:13px;margin-bottom:8px;
        max-width:82%;{'margin-right:auto' if msg['role']=='user' else 'margin-left:auto'}">
        {icon} {msg['content']}</div>""", unsafe_allow_html=True)

    # Suggested questions
    st.markdown('<p class="section-head" style="margin-top:12px">💡 Quick Questions</p>', unsafe_allow_html=True)
    suggestions = [
        "Best time to travel from PJ to KLCC?",
        "Is the Federal Highway bad now?",
        "Will rain affect my 5pm drive?",
        "Which roads are clear?",
    ]
    cols = st.columns(4)
    for i, s in enumerate(suggestions):
        if cols[i].button(s, key=f"sq_{i}", width='stretch'):
            st.session_state["pending_q"] = s

    user_input = st.chat_input("Ask about traffic, routes, or weather in Klang Valley...")

    if "pending_q" in st.session_state:
        user_input = st.session_state.pop("pending_q")

    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        with st.spinner("Thinking..."):
            reply = ask_traffic_assistant(
                HF_API_KEY, user_input,
                st.session_state.chat_history[:-1],
                traffic_data, weather_data
            )
        st.session_state.chat_history.append({"role":"assistant","content":reply})
        st.rerun()
