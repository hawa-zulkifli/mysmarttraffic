# 🚦 LALULINTAS — Klang Valley Traffic Intelligence
### Streamlit · TomTom Traffic API · HuggingFace flan-t5 · OpenWeatherMap

A real-time AI-powered traffic app for Klang Valley — **100% free APIs**.

---

## Features

| Feature | Technology | Cost |
|---|---|---|
| 🗺 Interactive live map | Folium + CartoDB Dark tiles | Free |
| 🚦 Live traffic flow tiles | TomTom Traffic Map API | Free (2,500 req/day) |
| 🛣 Road speed data | TomTom Flow Segment API | Free |
| 🔍 Route planner with ETA & delay | TomTom Routing API | Free |
| ☁ Live weather + rain probability | OpenWeatherMap API | Free (1,000 req/day) |
| 🤖 AI analysis report | HuggingFace flan-t5-large | Free (Inference API) |
| 💬 Traffic assistant chatbot | flan-t5 + rule-based engine | Free |
| 📈 Hourly congestion forecast | Altair chart | Free |
| 🌡 Traffic heatmap | Folium HeatMap plugin | Free |

---

## Quick Start (Local)

```bash
git clone https://github.com/YOUR_USERNAME/lalulintas.git
cd lalulintas
pip install -r requirements.txt
cp .env.example .env        # fill in your API keys
streamlit run app.py
```
Open http://localhost:8501

---

## API Keys (All Free)

### A) TomTom — Traffic + Routing
1. Sign up at https://developer.tomtom.com
2. Go to **My Apps → Create New App**
3. Enable: **Traffic API**, **Routing API**
4. Copy your API key
5. Add as `TOMTOM_API_KEY`

**Free tier:** 2,500 requests/day — sufficient for a prototype.
The app **probes only 4 road midpoints** per page load to stay well within limits.

### B) OpenWeatherMap — Weather
1. Sign up at https://openweathermap.org/api
2. Go to **API Keys** tab — default key is ready after signup
3. Add as `OPENWEATHER_API_KEY`

**Free tier:** 60 calls/minute, 1,000,000 calls/month.

### C) HuggingFace — AI Model (flan-t5-large)
1. Sign up at https://huggingface.co
2. Go to **Settings → Access Tokens → New Token** (read access is enough)
3. Add as `HF_API_KEY`

**Free tier:** Inference API is free for public models.
Model used: `google/flan-t5-large` — an instruction-tuned text generation model.

> **App works without any keys** — runs in demo mode with simulated KL traffic data and a rule-based AI engine.

---

## AI Architecture

```
User query
    │
    ▼
HuggingFace Inference API
  Model: google/flan-t5-large
  Input: live traffic context + question prompt
  Output: advisory text
    │
    ├── Success → display AI-generated advisory
    │
    └── Failure / no key
            │
            ▼
      Rule-based engine
      (KV-specific logic: road names, peak hours,
       rain thresholds, route recommendations)
```

The rule-based fallback is not a dummy — it reads live traffic & weather data and produces accurate, specific recommendations for Klang Valley roads.

---

## Deploy to Streamlit Community Cloud

```bash
# 1. Push to GitHub (secrets.toml is gitignored)
git init && git add . && git commit -m "init"
git remote add origin https://github.com/YOUR/lalulintas.git
git push -u origin main

# 2. Go to share.streamlit.io → New App
# 3. Repo: your repo | Branch: main | File: app.py
# 4. Advanced → Secrets → paste:

[secrets]
TOMTOM_API_KEY      = "..."
OPENWEATHER_API_KEY = "..."
HF_API_KEY          = "hf_..."

# 5. Deploy → live at yourapp.streamlit.app
```

---

## Project Structure

```
lalulintas/
├── app.py                     # Streamlit UI (4 tabs)
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   ├── config.toml            # Dark theme
│   └── secrets.toml           # Local secrets (gitignored)
└── modules/
    ├── weather.py             # OpenWeatherMap
    ├── traffic.py             # TomTom Flow + Routing APIs
    ├── ai_engine.py           # HuggingFace flan-t5 + rule-based fallback
    └── map_view.py            # Folium map + TomTom tile overlay
```

---

## Upgrading the AI

To use a more powerful free model, change `PRIMARY_MODEL` in `modules/ai_engine.py`:

| Model | Notes |
|---|---|
| `google/flan-t5-large` | Default — fast, good instruction following |
| `google/flan-t5-xl` | Larger, slower, better quality |
| `tiiuae/falcon-7b-instruct` | Strong open LLM, may need more tokens |
| `mistralai/Mistral-7B-Instruct-v0.2` | Excellent quality (may require HF Pro) |

---

## License
MIT
