"""
KrushiAI — Crop Advisor Module
Rule-based crop recommendation engine for Indian agriculture.
Scores crops by soil × season × water × region match.
"""

CROP_DATA = [
    {
        "name": "Pomegranate", "emoji": "🍎",
        "soils": ["Black", "Red", "Sandy Loam", "Laterite"],
        "seasons": ["Kharif", "Rabi", "Summer"],
        "water": ["Low", "Medium"],
        "regions": ["Maharashtra", "Gujarat", "Rajasthan", "Karnataka", "AP/Telangana"],
        "period": "5–7 months", "water_need": "Low (drought-tolerant)",
        "yield": "High — 20–25 t/ha",
        "best_for": "Dry & semi-arid regions",
        "tip": "Best suited for Maharashtra. Plant Feb–Mar or Aug–Sep. Requires well-drained soil.",
    },
    {
        "name": "Wheat", "emoji": "🌾",
        "soils": ["Black", "Loam", "Clay Loam", "Sandy Loam"],
        "seasons": ["Rabi"],
        "water": ["Medium", "High"],
        "regions": ["Punjab", "Haryana", "UP", "MP", "Rajasthan"],
        "period": "4–5 months", "water_need": "Medium (4–6 irrigations)",
        "yield": "High — 3–5 t/ha",
        "best_for": "Rabi (winter) season",
        "tip": "Sow Oct–Nov. Avoid late sowing — reduces yield significantly.",
    },
    {
        "name": "Rice", "emoji": "🍚",
        "soils": ["Clay", "Clay Loam", "Black"],
        "seasons": ["Kharif"],
        "water": ["High"],
        "regions": ["West Bengal", "UP", "AP/Telangana", "Tamil Nadu", "Karnataka"],
        "period": "3–6 months", "water_need": "High (flooded fields)",
        "yield": "High — 4–6 t/ha",
        "best_for": "Monsoon season with ample water",
        "tip": "Requires standing water. Best in clay-heavy soils that retain moisture.",
    },
    {
        "name": "Cotton", "emoji": "🌿",
        "soils": ["Black", "Red", "Loam"],
        "seasons": ["Kharif"],
        "water": ["Medium"],
        "regions": ["Maharashtra", "Gujarat", "AP/Telangana", "Haryana"],
        "period": "5–6 months", "water_need": "Medium",
        "yield": "Medium — 1.5–2.5 t/ha",
        "best_for": "Black cotton soil (Vidarbha, Gujarat)",
        "tip": "Sow Jun–Jul. Watch for bollworm infestation and pink bollworm in late season.",
    },
    {
        "name": "Sugarcane", "emoji": "🎋",
        "soils": ["Loam", "Clay Loam", "Black", "Sandy Loam"],
        "seasons": ["Kharif", "Rabi"],
        "water": ["High"],
        "regions": ["Maharashtra", "UP", "Tamil Nadu", "Karnataka"],
        "period": "12–18 months", "water_need": "High (1500–2500 mm/yr)",
        "yield": "Very High — 70–100 t/ha",
        "best_for": "High water availability areas near sugar mills",
        "tip": "Excellent cash crop. Requires consistent irrigation. Pair with drip for water savings.",
    },
    {
        "name": "Soybean", "emoji": "🫘",
        "soils": ["Black", "Loam", "Clay Loam"],
        "seasons": ["Kharif"],
        "water": ["Low", "Medium"],
        "regions": ["Maharashtra", "MP", "Rajasthan"],
        "period": "3–4 months", "water_need": "Low–Medium",
        "yield": "Medium — 1–2.5 t/ha",
        "best_for": "Maharashtra Kharif season",
        "tip": "Nitrogen fixer — improves soil for next crop. Great rotation partner with wheat.",
    },
    {
        "name": "Onion", "emoji": "🧅",
        "soils": ["Sandy Loam", "Loam", "Red"],
        "seasons": ["Rabi", "Kharif"],
        "water": ["Medium"],
        "regions": ["Maharashtra", "Karnataka", "MP", "Gujarat"],
        "period": "3–5 months", "water_need": "Medium",
        "yield": "High — 25–30 t/ha",
        "best_for": "Maharashtra (Nashik region) — India's top producer",
        "tip": "High market demand and export value. Avoid waterlogging to prevent neck rot.",
    },
    {
        "name": "Chickpea (Gram)", "emoji": "🫘",
        "soils": ["Sandy Loam", "Loam", "Red", "Black"],
        "seasons": ["Rabi"],
        "water": ["Low"],
        "regions": ["MP", "Rajasthan", "Maharashtra", "UP", "Karnataka"],
        "period": "3–4 months", "water_need": "Low (rainfed possible)",
        "yield": "Medium — 1–2 t/ha",
        "best_for": "Low water zones, Rabi season",
        "tip": "Drought tolerant once established. High protein value. Good market price.",
    },
    {
        "name": "Tomato", "emoji": "🍅",
        "soils": ["Sandy Loam", "Loam", "Red"],
        "seasons": ["Rabi", "Summer", "Kharif"],
        "water": ["Medium"],
        "regions": ["Maharashtra", "Karnataka", "AP/Telangana", "MP"],
        "period": "2–3 months", "water_need": "Medium",
        "yield": "Very High — 40–50 t/ha",
        "best_for": "Year-round cultivation with irrigation",
        "tip": "High value crop. Prone to late blight in humid conditions — apply fungicide preventively.",
    },
    {
        "name": "Maize (Corn)", "emoji": "🌽",
        "soils": ["Loam", "Sandy Loam", "Black", "Red"],
        "seasons": ["Kharif", "Rabi"],
        "water": ["Medium"],
        "regions": ["Karnataka", "AP/Telangana", "Maharashtra", "Bihar"],
        "period": "3–4 months", "water_need": "Medium",
        "yield": "High — 5–8 t/ha",
        "best_for": "Versatile — both Kharif and Rabi",
        "tip": "Good for food, feed, and industrial use. High demand from poultry industry.",
    },
    {
        "name": "Groundnut", "emoji": "🥜",
        "soils": ["Sandy Loam", "Red", "Loam"],
        "seasons": ["Kharif", "Rabi"],
        "water": ["Low", "Medium"],
        "regions": ["Gujarat", "AP/Telangana", "Tamil Nadu", "Maharashtra", "Rajasthan"],
        "period": "3–5 months", "water_need": "Low–Medium",
        "yield": "Medium — 1.5–3 t/ha",
        "best_for": "Sandy loam soils, semi-arid regions",
        "tip": "Drought tolerant once established. High oil content variety preferred for export.",
    },
    {
        "name": "Turmeric", "emoji": "🌿",
        "soils": ["Loam", "Clay Loam", "Red", "Sandy Loam"],
        "seasons": ["Kharif"],
        "water": ["Medium", "High"],
        "regions": ["Maharashtra", "AP/Telangana", "Tamil Nadu", "Odisha", "Karnataka"],
        "period": "7–9 months", "water_need": "Medium–High",
        "yield": "High — 25–30 t/ha (fresh)",
        "best_for": "Warm, humid climate with red/loamy soils",
        "tip": "High demand for medicinal and export market. Store in cool, dry conditions.",
    },
    {
        "name": "Banana", "emoji": "🍌",
        "soils": ["Loam", "Clay Loam", "Sandy Loam"],
        "seasons": ["Kharif", "Rabi", "Summer"],
        "water": ["High"],
        "regions": ["Maharashtra", "Tamil Nadu", "AP/Telangana", "Gujarat", "Karnataka"],
        "period": "10–14 months", "water_need": "High",
        "yield": "Very High — 30–40 t/ha",
        "best_for": "Warm tropical climate with reliable irrigation",
        "tip": "Jalgaon (Maharashtra) is a major banana hub. Drip irrigation highly recommended.",
    },
]

SOIL_OPTIONS   = ["Black", "Red", "Sandy Loam", "Loam", "Clay Loam", "Clay", "Laterite"]
SEASON_OPTIONS = ["Kharif (Jun–Oct)", "Rabi (Nov–Mar)", "Summer (Mar–Jun)"]
REGION_OPTIONS = [
    "Maharashtra", "Gujarat", "Punjab", "Haryana", "UP", "MP",
    "Karnataka", "AP/Telangana", "Tamil Nadu", "Rajasthan",
    "West Bengal", "Bihar", "Odisha", "Other",
]
WATER_OPTIONS = [
    "Low  —  Rainfed / Drought-prone",
    "Medium  —  Limited irrigation",
    "High  —  Good irrigation available",
]

_SEASON_MAP = {
    "Kharif (Jun–Oct)": "Kharif",
    "Rabi (Nov–Mar)":   "Rabi",
    "Summer (Mar–Jun)": "Summer",
}
_WATER_MAP = {
    "Low  —  Rainfed / Drought-prone":    "Low",
    "Medium  —  Limited irrigation":       "Medium",
    "High  —  Good irrigation available":  "High",
}


def get_crop_recommendations(soil: str, season: str, region: str, water: str) -> list[dict]:
    """
    Return top-5 scored crop recommendations.
    Scoring: soil match = 3 pts, season = 3 pts, water = 2 pts, region = 2 pts.
    """
    s = _SEASON_MAP.get(season, season)
    w = _WATER_MAP.get(water, water)

    results = []
    for crop in CROP_DATA:
        score = 0
        if soil   in crop["soils"]:   score += 3
        if s      in crop["seasons"]: score += 3
        if w      in crop["water"]:   score += 2
        if region in crop["regions"]: score += 2
        if score >= 3:
            results.append({**crop, "score": score})

    results.sort(key=lambda x: -x["score"])
    return results[:5]
