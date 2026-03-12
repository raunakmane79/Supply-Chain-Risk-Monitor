import requests
import pandas as pd


USGS_ALL_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def get_fallback_events() -> pd.DataFrame:
    """
    Fallback events so the app still works even if live APIs fail.
    """
    data = [
        {
            "event_type": "Flood",
            "title": "Flooding impacting port operations in China",
            "country": "China",
            "commodity": "Electronics",
            "severity": "Medium",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "source": "Fallback",
        },
        {
            "event_type": "Conflict",
            "title": "Conflict risk affecting metal shipments in Ukraine",
            "country": "Ukraine",
            "commodity": "Steel",
            "severity": "High",
            "latitude": 50.4501,
            "longitude": 30.5234,
            "source": "Fallback",
        },
        {
            "event_type": "Storm",
            "title": "Storm disruption near Chile logistics corridor",
            "country": "Chile",
            "commodity": "Copper",
            "severity": "Medium",
            "latitude": -33.4489,
            "longitude": -70.6693,
            "source": "Fallback",
        },
    ]
    return pd.DataFrame(data)


def classify_earthquake_commodity(magnitude: float) -> str:
    """
    Assign a likely impacted commodity bucket for earthquake events.
    """
    if magnitude >= 6.5:
        return "Semiconductor"
    if magnitude >= 5.0:
        return "Electronics"
    return "Machinery"


def classify_earthquake_severity(magnitude: float) -> str:
    if magnitude >= 6.5:
        return "High"
    if magnitude >= 5.0:
        return "Medium"
    return "Low"


def infer_country_from_place(place: str) -> str:
    """
    Simple country inference from USGS 'place' text.
    Not perfect, but good enough for MVP matching.
    """
    if not place:
        return "Unknown"

    country_keywords = [
        "Taiwan",
        "Japan",
        "China",
        "Chile",
        "Indonesia",
        "Mexico",
        "Turkey",
        "Greece",
        "India",
        "Philippines",
        "Alaska",
        "California",
        "Peru",
        "Argentina",
        "New Zealand",
        "Russia",
        "Papua New Guinea",
        "Iran",
    ]

    for keyword in country_keywords:
        if keyword.lower() in place.lower():
            return keyword

    # crude fallback: take text after "of"
    if " of " in place.lower():
        tail = place.split(" of ")[-1].strip()
        return tail

    return "Unknown"


def load_usgs_earthquakes(min_magnitude: float = 4.5, limit: int = 15) -> pd.DataFrame:
    """
    Load live earthquakes from USGS all-day GeoJSON feed.
    """
    response = requests.get(USGS_ALL_DAY_URL, timeout=20)
    response.raise_for_status()

    payload = response.json()
    features = payload.get("features", [])

    rows = []

    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [None, None])

        magnitude = props.get("mag")
        place = props.get("place", "Unknown location")

        if magnitude is None or magnitude < min_magnitude:
            continue

        longitude = coords[0] if len(coords) > 0 else None
        latitude = coords[1] if len(coords) > 1 else None

        rows.append(
            {
                "event_type": "Earthquake",
                "title": place,
                "country": infer_country_from_place(place),
                "commodity": classify_earthquake_commodity(float(magnitude)),
                "severity": classify_earthquake_severity(float(magnitude)),
                "latitude": latitude,
                "longitude": longitude,
                "source": "USGS",
                "magnitude": magnitude,
                "event_time": pd.to_datetime(props.get("time"), unit="ms", errors="coerce"),
                "url": props.get("url", ""),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.sort_values(by="magnitude", ascending=False).head(limit).reset_index(drop=True)
    return df


def load_all_events() -> pd.DataFrame:
    """
    Combine live USGS events with fallback events.
    """
    frames = []

    try:
        usgs_df = load_usgs_earthquakes()
        if not usgs_df.empty:
            frames.append(usgs_df)
    except Exception:
        pass

    fallback_df = get_fallback_events()
    frames.append(fallback_df)

    combined = pd.concat(frames, ignore_index=True, sort=False)

    # ensure expected columns exist
    expected_cols = [
        "event_type",
        "title",
        "country",
        "commodity",
        "severity",
        "latitude",
        "longitude",
        "source",
        "magnitude",
        "event_time",
        "url",
    ]

    for col in expected_cols:
        if col not in combined.columns:
            combined[col] = None

    combined = combined.dropna(subset=["latitude", "longitude"], how="any")
    combined = combined.reset_index(drop=True)
    return combined
