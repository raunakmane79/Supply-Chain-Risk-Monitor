import pandas as pd
import requests
from datetime import datetime, timezone

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

KEYWORDS = [
    "Iran conflict",
    "Strait of Hormuz",
    "Middle East conflict",
    "sanctions oil",
    "shipping disruption",
    "military strike oil",
    "port blockade",
    "Red Sea attack",
    "Taiwan tension",
    "Russia sanctions metals",
]

LOCATION_HINTS = {
    "iran": (32.0, 53.0, "Iran"),
    "strait of hormuz": (26.5, 56.25, "Iran"),
    "red sea": (20.0, 38.0, "Red Sea"),
    "taiwan": (23.7, 121.0, "Taiwan"),
    "russia": (61.5, 105.3, "Russia"),
    "ukraine": (48.4, 31.2, "Ukraine"),
    "israel": (31.0, 35.0, "Israel"),
    "china": (35.8, 104.1, "China"),
}

def infer_location(text: str):
    text = (text or "").lower()
    for key, (lat, lon, country) in LOCATION_HINTS.items():
        if key in text:
            return lat, lon, country
    return None, None, "Unknown"

def infer_severity(text: str):
    text = (text or "").lower()
    if any(x in text for x in ["war", "missile", "blockade", "strike", "attack", "sanction", "military"]):
        return "High"
    if any(x in text for x in ["tension", "warning", "disruption", "risk"]):
        return "Medium"
    return "Low"

def infer_commodity(text: str):
    text = (text or "").lower()
    if any(x in text for x in ["oil", "hormuz", "lng", "natural gas", "petroleum"]):
        return "Crude Oil"
    if any(x in text for x in ["semiconductor", "chip", "electronics", "taiwan"]):
        return "Semiconductor"
    if any(x in text for x in ["copper", "lithium", "nickel", "cobalt", "mining", "metal"]):
        return "Metals"
    if any(x in text for x in ["shipping", "port", "freight", "vessel", "container"]):
        return "Logistics"
    return "General"

def fetch_gdelt_conflict_events(max_records: int = 50) -> pd.DataFrame:
    rows = []

    for keyword in KEYWORDS:
        params = {
            "query": keyword,
            "mode": "ArtList",
            "maxrecords": 10,
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
                severity = infer_severity(seen_text)
                commodity = infer_commodity(seen_text)

                rows.append(
                    {
                        "title": title,
                        "event_type": "Conflict",
                        "country": country,
                        "commodity": commodity,
                        "severity": severity,
                        "source": source,
                        "event_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "latitude": lat,
                        "longitude": lon,
                        "url": url,
                    }
                )
        except Exception:
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["title"]).head(max_records)
    df = df.dropna(subset=["latitude", "longitude"])
    return df
