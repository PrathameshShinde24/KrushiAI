"""
KrushiAI — Weather & Disease Risk Module
Uses OpenWeatherMap Current Weather API (free tier).
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def _get_secret(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, "")
        except Exception:
            pass
    return val

OWM_KEY  = _get_secret("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> dict | None:
    """
    Fetch current weather for a city.
    Returns a clean dict or None on error / city not found.
    """
    if not OWM_KEY:
        return None
    try:
        resp = requests.get(
            BASE_URL,
            params={"q": city.strip(), "appid": OWM_KEY, "units": "metric"},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        d = resp.json()
        return {
            "city":       d["name"],
            "country":    d["sys"]["country"],
            "temp":       round(d["main"]["temp"], 1),
            "feels_like": round(d["main"]["feels_like"], 1),
            "humidity":   d["main"]["humidity"],
            "wind_kmh":   round(d["wind"]["speed"] * 3.6, 1),   # m/s → km/h
            "condition":  d["weather"][0]["description"].title(),
            "main":       d["weather"][0]["main"],               # Rain, Clouds, Clear …
            "icon_code":  d["weather"][0]["icon"],
        }
    except Exception:
        return None


def get_disease_risk(w: dict) -> dict:
    """
    Score pomegranate disease risk from weather metrics.
    High humidity + warm temps + rain = fungal outbreak conditions.
    """
    humidity = w["humidity"]
    temp     = w["temp"]
    main     = w["main"].lower()

    score = 0
    # Humidity (primary fungal driver)
    if   humidity >= 85: score += 3
    elif humidity >= 70: score += 2
    elif humidity >= 55: score += 1
    # Temperature (ideal fungal range 20–30 °C)
    if   20 <= temp <= 30: score += 2
    elif 15 <= temp <= 35: score += 1
    # Precipitation / mist
    if any(x in main for x in ["rain", "drizzle", "thunderstorm"]): score += 2
    elif any(x in main for x in ["mist", "fog", "haze"]):           score += 1

    if score >= 5:
        return {
            "level": "High", "color": "#f87171", "icon": "🔴",
            "advice": [
                "Apply preventive fungicide immediately (Mancozeb 2.5 g/L or Copper Oxychloride 3 g/L).",
                "Switch to drip irrigation — avoid all overhead watering.",
                "Inspect leaves daily for Alternaria, Anthracnose, and Cercospora symptoms.",
                "Prune dense canopy areas to improve air circulation.",
            ],
        }
    elif score >= 3:
        return {
            "level": "Medium", "color": "#fbbf24", "icon": "🟡",
            "advice": [
                "Monitor plants closely over the next 48–72 hours.",
                "Apply copper-based fungicide as a precaution.",
                "Avoid waterlogging — ensure drainage channels are clear.",
                "Check for early Cercospora leaf spot symptoms.",
            ],
        }
    else:
        return {
            "level": "Low", "color": "#10b981", "icon": "🟢",
            "advice": [
                "Conditions are favourable — maintain regular watering schedule.",
                "Good time to apply balanced NPK fertilizer.",
                "Ideal weather for pruning and canopy management.",
                "Continue weekly leaf inspections as a preventive measure.",
            ],
        }
