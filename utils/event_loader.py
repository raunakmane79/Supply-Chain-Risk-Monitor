import requests
import pandas as pd
from urllib.parse import quote_plus


USGS_ALL_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
GDELT_GEO_BASE_URL = "https://api.gdeltproject.org/api/v2/geo/geo"


def get_fallback_events() -> pd.DataFrame:
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
            "url": "",
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
            "url": "",
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
            "url": "",
        },
    ]
    return pd.DataFrame(data)


def classify_earthquake_commodity(magnitude: float) -> str:
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
    if not place:
        return "Unknown"

    country_keywords = [
        "Taiwan", "Japan", "China", "Chile", "Indonesia", "Mexico", "Turkey",
        "Greece", "India", "Philippines", "Alaska", "California", "Peru",
        "Argentina", "New Zealand", "Russia", "Papua New Guinea", "Iran",
        "Ukraine", "Israel", "Panama", "Egypt", "Singapore", "Vietnam"
    ]

    for keyword in country_keywords:
        if keyword.lower() in place.lower():
            return keyword

    if " of " in place.lower():
        return place.split(" of ")[-1].strip()

    return "Unknown"


def load_usgs_earthquakes(min_magnitude: float = 4.5, limit: int = 15) -> pd.DataFrame:
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

    return df.sort_values(by="magnitude", ascending=False).head(limit).reset_index(drop=True)


GDELT_QUERY_CONFIGS = [
    {
        "name": "Port / Shipping Disruption",
        "query": '"port" OR shipping OR blockade OR "supply chain" OR congestion',
        "event_type": "Logistics",
        "commodity": "Shipping",
        "severity": "Medium",
    },
    {
        "name": "Protest / Strike",
        "query": "protest OR strike OR labor OR union OR shutdown",
        "event_type": "Protest",
        "commodity": "Manufacturing",
        "severity": "Medium",
    },
    {
        "name": "Conflict / Sanctions",
        "query": "conflict OR sanctions OR attack OR war OR missile",
        "event_type": "Conflict",
        "commodity": "Oil",
        "severity": "High",
    },
    {
        "name": "Flood / Storm",
        "query": "flood OR storm OR cyclone OR typhoon OR landslide",
        "event_type": "Flood",
        "commodity": "Logistics",
        "severity": "Medium",
    },
]


def _safe_prop(props: dict, *keys, default=""):
    for key in keys:
        value = props.get(key)
        if value not in (None, ""):
            return value
    return default


def load_gdelt_geo_events(max_per_query: int = 15) -> pd.DataFrame:
    rows = []

    for cfg in GDELT_QUERY_CONFIGS:
        params = {
            "query": cfg["query"],
            "format": "geojson",
            "timespan": "24h",
            "sort": "datedesc",
        }

        response = requests.get(GDELT_GEO_BASE_URL, params=params, timeout=25)
        response.raise_for_status()

        payload = response.json()
        features = payload.get("features", [])

        for feature in features[:max_per_query]:
            geometry = feature.get("geometry", {})
            props = feature.get("properties", {})
            coords = geometry.get("coordinates", [None, None])

            longitude = coords[0] if len(coords) > 0 else None
            latitude = coords[1] if len(coords) > 1 else None

            if latitude is None or longitude is None:
                continue

            title = _safe_prop(
                props,
                "name",
                "title",
                "label",
                "description",
                default=cfg["name"],
            )

            country = _safe_prop(
                props,
                "country",
                "countryname",
                "adm0name",
                "location",
                default="Unknown",
            )

            article_url = _safe_prop(props, "url", "shareurl", "articleurl", default="")
            article_time = _safe_prop(props, "date", "seendate", "datetime", default="")

            rows.append(
                {
                    "event_type": cfg["event_type"],
                    "title": str(title)[:180],
                    "country": country,
                    "commodity": cfg["commodity"],
                    "severity": cfg["severity"],
                    "latitude": latitude,
                    "longitude": longitude,
                    "source": "GDELT",
                    "magnitude": None,
                    "event_time": pd.to_datetime(article_time, errors="coerce"),
                    "url": article_url,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["title", "latitude", "longitude"]).reset_index(drop=True)
    return df


def load_all_events() -> pd.DataFrame:
    frames = []

    try:
        usgs_df = load_usgs_earthquakes()
        if not usgs_df.empty:
            frames.append(usgs_df)
    except Exception:
        pass

    try:
        gdelt_df = load_gdelt_geo_events()
        if not gdelt_df.empty:
            frames.append(gdelt_df)
    except Exception:
        pass

    fallback_df = get_fallback_events()
    frames.append(fallback_df)

    combined = pd.concat(frames, ignore_index=True, sort=False)

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
    combined = combined.sort_values(
        by=["source", "event_time"],
        ascending=[True, False],
        na_position="last"
    ).reset_index(drop=True)

    return combined
