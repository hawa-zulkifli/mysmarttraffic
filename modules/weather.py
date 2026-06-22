"""
modules/weather.py
------------------
Live weather for Kuala Lumpur via OpenWeatherMap free API.
Free tier: 1,000 calls/day.
"""

import requests
import streamlit as st

KL_LAT, KL_LON = 3.1390, 101.6869

WEATHER_ICONS = {
    "thunderstorm": "⛈", "drizzle": "🌦", "rain": "🌧",
    "snow": "❄️", "mist": "🌫", "fog": "🌫", "haze": "🌫",
    "clear": "☀️", "clouds": "⛅",
}


@st.cache_data(ttl=300)
def get_weather(api_key: str) -> dict:
    if not api_key:
        return _mock_weather()
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": KL_LAT, "lon": KL_LON, "appid": api_key, "units": "metric"}
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        d = resp.json()

        main       = d["main"]
        wind       = d.get("wind", {})
        vis        = d.get("visibility", 10000)
        weather    = d["weather"][0]
        main_cond  = weather["main"].lower()
        clouds     = d.get("clouds", {}).get("all", 0)

        if any(w in main_cond for w in ("rain","thunder","drizzle")):
            rain_prob = min(95, 60 + clouds // 3)
        elif clouds > 75:
            rain_prob = min(70, 30 + clouds // 4)
        else:
            rain_prob = max(5, clouds // 5)

        icon = next((v for k, v in WEATHER_ICONS.items() if k in main_cond), "🌤")

        return {
            "city":             d.get("name", "Kuala Lumpur"),
            "temp_c":           round(main["temp"]),
            "feels_like":       round(main["feels_like"]),
            "feels_like_delta": f"Feels {round(main['feels_like'])}°C",
            "humidity":         main["humidity"],
            "wind_kmh":         round(wind.get("speed", 0) * 3.6),
            "visibility_km":    round(vis / 1000, 1),
            "description":      weather["description"],
            "rain_prob_pct":    rain_prob,
            "icon":             icon,
            "clouds_pct":       clouds,
        }
    except Exception:
        return _mock_weather()


def _mock_weather() -> dict:
    return {
        "city": "Kuala Lumpur", "temp_c": 31, "feels_like": 35,
        "feels_like_delta": "Feels 35°C", "humidity": 82, "wind_kmh": 14,
        "visibility_km": 7.5, "description": "partly cloudy (demo)",
        "rain_prob_pct": 65, "icon": "⛅", "clouds_pct": 60,
    }
