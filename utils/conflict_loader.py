import pandas as pd
import requests
from datetime import datetime, timezone

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

KEYWORDS = [
    "Iran conflict oil shipping",
    "Strait of Hormuz disruption",
    "Middle East conflict oil gas",
    "Red Sea attack shipping",
    "Taiwan tension semiconductor",
    "Russia sanctions metals energy",
    "Chile mining strike copper",
    "China export restrictions rare earth",
]

LOCATION_HINTS = {
    "iran": (32.0, 53.0, "Iran"),
    "strait of hormuz": (26.5667, 56.25, "Iran"),
    "middle east": (25.276987, 55.296249, "Middle East"),
    "red sea": (20.0, 38.0, "Red Sea"),
    "taiwan": (23.6978, 120.9605, "Taiwan"),
    "russia": (61.5240, 105.3188, "Russia"),
    "ukraine": (48.3794, 31.1656, "Ukraine"),
    "chile": (-35.6751, -71.5430, "Chile"),
    "china": (35.8617, 104.1954, "China"),
    "israel": (31.0461, 34.8516, "Israel"),
    "gaza": (31.3547, 34.3088, "Gaza"),
    "yemen": (15.5527, 48.5164, "Yemen"),
    "peru": (-9.19, -75.0152, "Peru"),
}

def infer_location(text: str):
    text = (text or "").lower()
    for key, (lat, lon, country) in LOCATION_HINTS.items():
        if key in text:
            return lat, lon, country
    return None, None, "Unknown"


def classify_event_type(text: str):
    text = (text or "").lower()

    if any(x in text for x in ["sanction", "export ban", "trade restriction", "tariff"]):
        return "Sanctions"
    if any(x in text for x in ["shipping", "port", "freight", "vessel", "container", "strait", "blockade"]):
        return "Shipping Disruption"
    if any(x in text for x in ["attack", "missile", "military", "war", "conflict", "strike"]):
        return "Conflict"
    return "Geopolitical Risk"


def infer_severity(text: str):
    text = (text or "").lower()

    if any(x in text for x in ["war", "missile", "blockade", "attack", "airstrike", "military strike"]):
        return "High"
    if any(x in text for x in ["sanction", "disruption", "warning", "tension", "strike"]):
        return "Medium"
    return "Low"


def infer_commodity(text: str):
    text = (text or "").lower()

    if any(x in text for x in ["oil", "hormuz", "lng", "natural gas", "petroleum", "crude"]):
        return "Crude Oil"
    if any(x in text for x in ["semiconductor", "chip", "electronics", "taiwan", "microchip"]):
        return "Semiconductor"
    if any(x in text for x in ["copper", "lithium", "nickel", "cobalt", "mining", "metal", "rare earth"]):
        return "Metals"
    if any(x in text for x in ["shipping", "port", "freight", "vessel", "container", "strait"]):
        return "Logistics"
    return "General"


def fetch_gdelt_conflict_events(max_records: int = 50) -> pd.DataFrame:
    rows = []

    for keyword in KEYWORDS:
        params = {
            "query": keyword,
            "mode": "ArtList",
            "maxrecords": 15,
            "format": "json",
            "sort": "DateDesc",
        }

        try:
            response = requests.get(GDELT_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])

            for article in articles:
                title = article.get("title", "")
                source = article.get("sourceCommonName", "GDELT")
                url = article.get("url", "")
                seen_text = f"{title} {keyword}"

                lat, lon, country = infer_location(seen_text)
                if lat is None or lon is None:
                    continue

                rows.append(
                    {
                        "title": title,
                        "event_type": classify_event_type(seen_text),
                        "country": country,
                        "commodity": infer_commodity(seen_text),
                        "severity": infer_severity(seen_text),
                        "source": source,
                        "event_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "latitude": lat,
                        "longitude": lon,
                        "url": url,
                    }
                )

        except Exception:
            continue

    if not rows:
        return pd.DataFrame(
            columns=[
                "title", "event_type", "country", "commodity", "severity",
                "source", "event_time", "latitude", "longitude", "url"
            ]
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["title"]).head(max_records)
    return df
