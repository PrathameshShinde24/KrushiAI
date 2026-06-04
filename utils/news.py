"""
KrushiAI — Agri News & Farming Tips Module
Uses NewsAPI.org to fetch latest agricultural news (cached 1 hour).
"""

import os
import requests
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _get_secret(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, "")
        except Exception:
            pass
    return val

NEWS_KEY = _get_secret("NEWS_API_KEY")
NEWS_URL = "https://newsapi.org/v2/everything"

# ── Rotating farming tips (shown daily, cycles through list) ─────────────────

FARMING_TIPS = [
    ("🌱", "Soil Preparation",
     "Always test your soil before the season. A Soil Health Card helps apply the right fertilizers and avoids wastage — apply at your nearest KVK."),
    ("💧", "Water Management",
     "Drip irrigation saves up to 50% water vs flood irrigation. Apply for PMKSY subsidy (55% for small farmers) to install it affordably."),
    ("🔬", "Early Disease Detection",
     "Inspect leaves every week — early detection of Alternaria or Anthracnose prevents 60–70% of yield loss. Use KrushiAI Scanner regularly."),
    ("🌿", "Organic Matter",
     "Add compost or farmyard manure (FYM) before planting to improve soil structure, water retention, and microbial activity."),
    ("🌾", "Crop Rotation",
     "Rotate crops every season to break pest cycles. Legumes like chickpea and soybean fix nitrogen and reduce fertilizer costs by up to 30%."),
    ("☀️", "Optimal Planting Time",
     "Sow seeds when soil temperature matches crop requirements. Pomegranate planting is best in Feb–Mar or Aug–Sep in Maharashtra."),
    ("🛡️", "Preventive Spraying",
     "Apply a preventive fungicide spray before monsoon season. Mancozeb 2.5 g/L or Copper Oxychloride 3 g/L works for most fungal diseases."),
    ("📦", "Post-Harvest Care",
     "Store harvested produce in cool, dry conditions. Even a 5°C reduction in temperature significantly extends shelf life and reduces losses."),
    ("🐛", "IPM Approach",
     "Integrated Pest Management (IPM) reduces chemical use by 30–40%. Use sticky traps, neem oil, and biological controls as first line of defense."),
    ("💰", "Better Market Prices",
     "Register on eNAM (National Agriculture Market) to sell directly to buyers across India and get better prices than local mandi rates."),
    ("🌡️", "Heat Stress Management",
     "During heatwaves, spray kaolin clay solution on leaves or apply mulch around the plant base to reduce soil temperature by 4–6°C."),
    ("🌧️", "Monsoon Preparation",
     "Clear drainage channels before monsoon arrives. Waterlogging for even 24 hours causes severe root damage and accelerates fungal spread."),
    ("🧪", "Foliar Nutrition",
     "Apply micronutrient foliar sprays (Zinc, Boron, Magnesium) during flowering and fruiting stages to improve fruit quality and yield."),
    ("🌻", "Intercropping Benefits",
     "Intercropping pomegranate with legumes like groundnut during early years improves soil fertility and provides additional income."),
    ("📱", "Digital Farming Tools",
     "Use KrushiAI regularly to track your field health over time. Data from multiple scans helps identify recurring disease patterns early."),
]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_agri_news(query: str = "agriculture India farming") -> list[dict]:
    """
    Fetch latest agri news from NewsAPI.
    Results cached for 1 hour to stay within free-tier limits.
    """
    if not NEWS_KEY:
        return []
    try:
        resp = requests.get(
            NEWS_URL,
            params={
                "q":        query,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 15,
                "apiKey":   NEWS_KEY,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        results = []
        for a in articles:
            title = a.get("title", "")
            if not title or title == "[Removed]":
                continue
            results.append({
                "title":       title,
                "source":      a.get("source", {}).get("name", "News"),
                "description": (a.get("description") or "")[:200],
                "url":         a.get("url", "#"),
                "image":       a.get("urlToImage"),
                "published":   _fmt_date(a.get("publishedAt", "")),
            })
        return results[:10]
    except Exception:
        return []


def get_tip_of_day() -> tuple:
    """Return today's farming tip based on day-of-year, cycling through all tips."""
    idx = datetime.now().timetuple().tm_yday % len(FARMING_TIPS)
    return FARMING_TIPS[idx]


def get_all_tips() -> list[tuple]:
    return FARMING_TIPS


def _fmt_date(dt_str: str) -> str:
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return dt_str[:10] if dt_str else ""
