import sys
from pathlib import Path
import json
import math
import heapq

sys.path.append(str(Path(__file__).parent.resolve()))

import streamlit as st
import pandas as pd
import pydeck as pdk

from utils.bom_parser import load_bom, validate_bom, clean_bom, get_bom_template
from utils.risk_engine import analyze_bom_risk
from utils.recommender import add_recommendations
from utils.event_loader import load_all_events
from utils.ai_engine import (
    generate_ai_risk_commentary,
    rank_alternate_sources,
    generate_scenario_commentary,
)


st.set_page_config(
    page_title="Supply Chain Risk Monitor",
    page_icon="🌍",
    layout="wide"
)


SCENARIOS = {
    "Strait of Hormuz Closure": {
        "countries": ["Iran"],
        "commodities": ["Crude Oil", "Natural Gas", "LNG", "Petrochemicals", "Oil"],
        "event_type": "Conflict",
        "severity": "High",
        "latitude": 26.5667,
        "longitude": 56.25,
    },
    "Taiwan Semiconductor Disruption": {
        "countries": ["Taiwan"],
        "commodities": ["Semiconductor", "Microchips", "Memory Chips", "Electronics"],
        "event_type": "Conflict",
        "severity": "High",
        "latitude": 23.7,
        "longitude": 121.0,
    },
    "Chile Copper Strike": {
        "countries": ["Chile"],
        "commodities": ["Copper"],
        "event_type": "Protest",
        "severity": "High",
        "latitude": -33.4489,
        "longitude": -70.6693,
    },
    "Red Sea Shipping Delays": {
        "countries": ["Yemen", "Egypt", "Red Sea"],
        "commodities": ["Shipping", "Logistics", "Imported Parts"],
        "event_type": "Shipping Disruption",
        "severity": "High",
        "latitude": 20.0,
        "longitude": 38.0,
    },
}

PORTS = {
    "Shanghai": {"lat": 31.2304, "lon": 121.4737, "region": "Asia"},
    "Shenzhen": {"lat": 22.5431, "lon": 114.0579, "region": "Asia"},
    "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "region": "Asia"},
    "Singapore": {"lat": 1.2903, "lon": 103.8519, "region": "Asia"},
    "Busan": {"lat": 35.1796, "lon": 129.0756, "region": "Asia"},
    "Kaohsiung": {"lat": 22.6273, "lon": 120.3014, "region": "Asia"},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503, "region": "Asia"},
    "Manila": {"lat": 14.5995, "lon": 120.9842, "region": "Asia"},
    "Jakarta": {"lat": -6.2088, "lon": 106.8456, "region": "Asia"},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "region": "Asia"},
    "Chennai": {"lat": 13.0827, "lon": 80.2707, "region": "Asia"},
    "Dubai": {"lat": 25.2048, "lon": 55.2708, "region": "Middle East"},
    "Jeddah": {"lat": 21.4858, "lon": 39.1925, "region": "Middle East"},
    "Dammam": {"lat": 26.4207, "lon": 50.0888, "region": "Middle East"},
    "Rotterdam": {"lat": 51.9244, "lon": 4.4777, "region": "Europe"},
    "Hamburg": {"lat": 53.5511, "lon": 9.9937, "region": "Europe"},
    "Antwerp": {"lat": 51.2194, "lon": 4.4025, "region": "Europe"},
    "Valencia": {"lat": 39.4699, "lon": -0.3763, "region": "Europe"},
    "Piraeus": {"lat": 37.9420, "lon": 23.6465, "region": "Europe"},
    "London": {"lat": 51.5072, "lon": -0.1276, "region": "Europe"},
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "region": "North America"},
    "Long Beach": {"lat": 33.7701, "lon": -118.1937, "region": "North America"},
    "Houston": {"lat": 29.7604, "lon": -95.3698, "region": "North America"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "region": "North America"},
    "Savannah": {"lat": 32.0809, "lon": -81.0912, "region": "North America"},
    "Vancouver": {"lat": 49.2827, "lon": -123.1207, "region": "North America"},
    "Panama City": {"lat": 8.9824, "lon": -79.5199, "region": "North America"},
    "Santos": {"lat": -23.9608, "lon": -46.3336, "region": "South America"},
    "Callao": {"lat": -12.0621, "lon": -77.1353, "region": "South America"},
    "Buenos Aires": {"lat": -34.6037, "lon": -58.3816, "region": "South America"},
    "Durban": {"lat": -29.8587, "lon": 31.0218, "region": "Africa"},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241, "region": "Africa"},
    "Mombasa": {"lat": -4.0435, "lon": 39.6682, "region": "Africa"},
    "Lagos": {"lat": 6.5244, "lon": 3.3792, "region": "Africa"},
    "Sydney": {"lat": -33.8688, "lon": 151.2093, "region": "Oceania"},
    "Melbourne": {"lat": -37.8136, "lon": 144.9631, "region": "Oceania"},
}

ROUTE_NODES = {
    "SouthChinaSea": {"lat": 12.0, "lon": 114.0},
    "EastChinaSea": {"lat": 28.0, "lon": 125.0},
    "SeaOfJapan": {"lat": 37.0, "lon": 136.0},
    "TaiwanStrait": {"lat": 24.0, "lon": 119.5},
    "PhilippineSea": {"lat": 18.0, "lon": 135.0},
    "Malacca": {"lat": 2.5, "lon": 101.0},
    "JavaSea": {"lat": -5.0, "lon": 112.0},
    "TimorSea": {"lat": -11.0, "lon": 125.0},
    "IndianOceanEast": {"lat": -12.0, "lon": 95.0},
    "IndianOceanMid": {"lat": -10.0, "lon": 80.0},
    "ArabianSea": {"lat": 15.0, "lon": 65.0},
    "BayOfBengal": {"lat": 15.0, "lon": 88.0},
    "Hormuz": {"lat": 26.5667, "lon": 56.25},
    "GulfOfAden": {"lat": 12.0, "lon": 48.0},
    "RedSea": {"lat": 20.0, "lon": 38.0},
    "Suez": {"lat": 29.9668, "lon": 32.5498},
    "MediterraneanEast": {"lat": 34.5, "lon": 28.0},
    "MediterraneanCentral": {"lat": 36.0, "lon": 18.0},
    "MediterraneanWest": {"lat": 37.0, "lon": 2.0},
    "Gibraltar": {"lat": 36.1408, "lon": -5.3536},
    "NorthSea": {"lat": 55.0, "lon": 3.0},
    "BalticGate": {"lat": 56.0, "lon": 10.0},
    "PanamaCanal": {"lat": 9.08, "lon": -79.68},
    "PacificMid": {"lat": 25.0, "lon": -160.0},
    "NorthPacificWest": {"lat": 35.0, "lon": 160.0},
    "NorthPacificEast": {"lat": 35.0, "lon": -145.0},
    "SouthPacificMid": {"lat": -20.0, "lon": -140.0},
    "CapeOfGoodHope": {"lat": -34.0, "lon": 18.5},
    "SouthAtlantic": {"lat": -20.0, "lon": -10.0},
    "NorthAtlantic": {"lat": 35.0, "lon": -30.0},
    "WestAfrica": {"lat": 5.0, "lon": -5.0},
    "EastAfrica": {"lat": -2.0, "lon": 42.0},
    "TasmanSea": {"lat": -35.0, "lon": 155.0},
}

SEA_LANE_EDGES = [
    ("Shanghai", "EastChinaSea"),
    ("Shenzhen", "SouthChinaSea"),
    ("Hong Kong", "SouthChinaSea"),
    ("Busan", "SeaOfJapan"),
    ("Kaohsiung", "TaiwanStrait"),
    ("Tokyo", "EastChinaSea"),
    ("Manila", "PhilippineSea"),
    ("Jakarta", "JavaSea"),
    ("Singapore", "Malacca"),
    ("Mumbai", "ArabianSea"),
    ("Chennai", "BayOfBengal"),
    ("Dubai", "Hormuz"),
    ("Dammam", "Hormuz"),
    ("Jeddah", "RedSea"),
    ("Rotterdam", "NorthSea"),
    ("Hamburg", "NorthSea"),
    ("Antwerp", "NorthSea"),
    ("Valencia", "MediterraneanWest"),
    ("Piraeus", "MediterraneanEast"),
    ("London", "NorthSea"),
    ("Los Angeles", "NorthPacificEast"),
    ("Long Beach", "NorthPacificEast"),
    ("Vancouver", "NorthPacificEast"),
    ("Houston", "PanamaCanal"),
    ("New York", "NorthAtlantic"),
    ("Savannah", "NorthAtlantic"),
    ("Panama City", "PanamaCanal"),
    ("Santos", "SouthAtlantic"),
    ("Callao", "SouthPacificMid"),
    ("Buenos Aires", "SouthAtlantic"),
    ("Durban", "CapeOfGoodHope"),
    ("Cape Town", "CapeOfGoodHope"),
    ("Mombasa", "EastAfrica"),
    ("Lagos", "WestAfrica"),
    ("Sydney", "TasmanSea"),
    ("Melbourne", "TasmanSea"),

    ("SeaOfJapan", "EastChinaSea"),
    ("EastChinaSea", "TaiwanStrait"),
    ("EastChinaSea", "NorthPacificWest"),
    ("TaiwanStrait", "SouthChinaSea"),
    ("TaiwanStrait", "PhilippineSea"),
    ("SouthChinaSea", "Malacca"),
    ("SouthChinaSea", "PhilippineSea"),
    ("PhilippineSea", "NorthPacificWest"),
    ("NorthPacificWest", "PacificMid"),
    ("NorthPacificEast", "PacificMid"),
    ("PacificMid", "NorthPacificEast"),

    ("JavaSea", "Malacca"),
    ("JavaSea", "TimorSea"),
    ("TimorSea", "IndianOceanEast"),
    ("TasmanSea", "SouthPacificMid"),

    ("Malacca", "IndianOceanEast"),
    ("BayOfBengal", "Malacca"),
    ("BayOfBengal", "IndianOceanMid"),
    ("IndianOceanEast", "IndianOceanMid"),
    ("IndianOceanMid", "ArabianSea"),
    ("IndianOceanMid", "CapeOfGoodHope"),
    ("ArabianSea", "Hormuz"),
    ("ArabianSea", "GulfOfAden"),
    ("EastAfrica", "GulfOfAden"),
    ("EastAfrica", "CapeOfGoodHope"),
    ("GulfOfAden", "RedSea"),
    ("RedSea", "Suez"),
    ("Suez", "MediterraneanEast"),
    ("MediterraneanEast", "MediterraneanCentral"),
    ("MediterraneanCentral", "MediterraneanWest"),
    ("MediterraneanWest", "Gibraltar"),
    ("Gibraltar", "NorthSea"),
    ("Gibraltar", "NorthAtlantic"),
    ("Gibraltar", "WestAfrica"),
    ("WestAfrica", "SouthAtlantic"),
    ("CapeOfGoodHope", "SouthAtlantic"),
    ("SouthAtlantic", "NorthAtlantic"),
    ("SouthAtlantic", "PanamaCanal"),
    ("PanamaCanal", "SouthPacificMid"),
    ("PanamaCanal", "NorthPacificEast"),
    ("NorthAtlantic", "NorthSea"),
]

SCENARIO_ZONES = {
    "Strait of Hormuz Closure": {
        "center": [56.25, 26.5667],
        "radius_km": 450,
        "severity": "High",
        "impact": "Oil, LNG, Middle East shipping",
    },
    "Red Sea Disruption": {
        "center": [38.0, 20.0],
        "radius_km": 900,
        "severity": "High",
        "impact": "Asia-Europe shipping",
    },
    "Suez Canal Blockage": {
        "center": [32.5498, 29.9668],
        "radius_km": 250,
        "severity": "High",
        "impact": "Europe-Asia maritime corridor",
    },
    "Panama Canal Restriction": {
        "center": [-79.68, 9.08],
        "radius_km": 250,
        "severity": "High",
        "impact": "Atlantic-Pacific flows",
    },
    "Taiwan Strait Tension": {
        "center": [119.5, 24.0],
        "radius_km": 500,
        "severity": "High",
        "impact": "Semiconductor and East Asia shipping",
    },
    "Cape Diversion Pressure": {
        "center": [18.5, -34.0],
        "radius_km": 500,
        "severity": "Medium",
        "impact": "Long-route diversion stress",
    },
    "South China Sea Tension": {
        "center": [114.0, 12.0],
        "radius_km": 800,
        "severity": "High",
        "impact": "Asia intra-regional trade and electronics flows",
    },
    "North Pacific Storm Corridor": {
        "center": [-160.0, 25.0],
        "radius_km": 1200,
        "severity": "Medium",
        "impact": "Trans-Pacific shipping delays",
    },
}


@st.cache_data(ttl=900)
def get_live_events() -> pd.DataFrame:
    return load_all_events()


@st.cache_data(ttl=900, show_spinner=False)
def cached_ai_risk_commentary(events_summary_json: str, bom_summary_json: str):
    return generate_ai_risk_commentary(
        json.loads(events_summary_json),
        json.loads(bom_summary_json),
    )


@st.cache_data(ttl=900, show_spinner=False)
def cached_ai_alternate_sources(part_context_json: str):
    return rank_alternate_sources(json.loads(part_context_json))


@st.cache_data(ttl=900, show_spinner=False)
def cached_ai_scenario_commentary(scenario_context_json: str):
    return generate_scenario_commentary(json.loads(scenario_context_json))


def apply_scenario(events_df: pd.DataFrame, selected_scenario: str) -> pd.DataFrame:
    if selected_scenario == "None":
        return events_df

    scenario = SCENARIOS[selected_scenario]

    synthetic = pd.DataFrame([
        {
            "event_type": scenario["event_type"],
            "title": selected_scenario,
            "country": ", ".join(scenario["countries"]),
            "commodity": scenario["commodities"][0],
            "severity": scenario["severity"],
            "latitude": scenario["latitude"],
            "longitude": scenario["longitude"],
            "source": "Scenario Simulator",
            "magnitude": None,
            "event_time": pd.Timestamp.utcnow(),
            "url": "",
        }
    ])

    if events_df.empty:
        return synthetic

    return pd.concat([events_df, synthetic], ignore_index=True)


def add_map_styles(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.copy()

    def pick_color(row):
        event_type = row.get("event_type", "")
        severity = row.get("severity", "")

        if event_type == "Conflict":
            return [220, 38, 38, 210]
        if event_type == "Sanctions":
            return [249, 115, 22, 210]
        if event_type == "Shipping Disruption":
            return [245, 158, 11, 210]
        if event_type == "Scenario":
            return [99, 102, 241, 210]

        if severity == "High":
            return [220, 38, 38, 180]
        if severity == "Medium":
            return [245, 158, 11, 180]
        return [34, 197, 94, 180]

    def pick_radius(row):
        severity = row.get("severity", "")
        if severity == "High":
            return 140000
        if severity == "Medium":
            return 90000
        return 60000

    df["color"] = df.apply(pick_color, axis=1)
    df["radius"] = df.apply(pick_radius, axis=1)

    return df


def render_event_map(events_df: pd.DataFrame):
    if events_df.empty:
        st.info("No events available for map display.")
        return

    map_df = add_map_styles(events_df)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position='[longitude, latitude]',
        get_fill_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_min_pixels=8,
        radius_max_pixels=40,
        line_width_min_pixels=1,
    )

    view_state = pdk.ViewState(
        latitude=20,
        longitude=0,
        zoom=1.1,
        pitch=0,
    )

    tooltip = {
        "html": """
        <b>Event:</b> {title}<br/>
        <b>Type:</b> {event_type}<br/>
        <b>Country:</b> {country}<br/>
        <b>Commodity:</b> {commodity}<br/>
        <b>Severity:</b> {severity}<br/>
        <b>Source:</b> {source}<br/>
        <b>Time:</b> {event_time}
        """,
        "style": {"backgroundColor": "black", "color": "white"},
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="light",
    )

    st.pydeck_chart(deck, use_container_width=True)


def render_timeline(events_df: pd.DataFrame):
    if events_df.empty or "event_time" not in events_df.columns:
        st.info("No timeline data available.")
        return

    df = events_df.copy()
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce", utc=True)
    df = df.dropna(subset=["event_time"])

    if df.empty:
        st.info("No valid event times available.")
        return

    df["hour_bucket"] = df["event_time"].dt.floor("h")
    timeline = df.groupby("hour_bucket").size().reset_index(name="event_count")

    if timeline.empty:
        st.info("No timeline data available.")
        return

    st.line_chart(timeline.set_index("hour_bucket"))


REGION_MAP = {
    "China": "Asia",
    "Taiwan": "Asia",
    "Japan": "Asia",
    "India": "Asia",
    "South Korea": "Asia",
    "Singapore": "Asia",
    "Vietnam": "Asia",
    "Philippines": "Asia",
    "Indonesia": "Asia",
    "Iran": "Middle East",
    "Israel": "Middle East",
    "Egypt": "Middle East",
    "Yemen": "Middle East",
    "Saudi Arabia": "Middle East",
    "UAE": "Middle East",
    "Ukraine": "Europe",
    "Russia": "Europe",
    "Germany": "Europe",
    "Netherlands": "Europe",
    "Belgium": "Europe",
    "Chile": "South America",
    "Brazil": "South America",
    "Peru": "South America",
    "Argentina": "South America",
    "United States": "North America",
    "Canada": "North America",
    "Mexico": "North America",
    "South Africa": "Africa",
    "Kenya": "Africa",
    "Nigeria": "Africa",
    "Australia": "Oceania",
}


def add_region(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.copy()
    df["region"] = df["country"].map(REGION_MAP).fillna("Other")
    return df


def render_regional_summary(events_df: pd.DataFrame):
    if events_df.empty:
        st.info("No regional data available.")
        return

    df = add_region(events_df)
    summary = (
        df.groupby("region")
        .agg(
            live_events=("title", "count"),
            countries=("country", "nunique")
        )
        .reset_index()
        .sort_values("live_events", ascending=False)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def get_node_coord(name):
    if name in PORTS:
        return PORTS[name]["lon"], PORTS[name]["lat"]
    if name in ROUTE_NODES:
        return ROUTE_NODES[name]["lon"], ROUTE_NODES[name]["lat"]
    raise KeyError(f"Unknown node: {name}")


def build_graph():
    graph = {}
    for a, b in SEA_LANE_EDGES:
        lon1, lat1 = get_node_coord(a)
        lon2, lat2 = get_node_coord(b)
        dist = haversine_km(lon1, lat1, lon2, lat2)

        graph.setdefault(a, []).append((b, dist))
        graph.setdefault(b, []).append((a, dist))
    return graph


def shortest_path(graph, start, end):
    pq = [(0, start, [])]
    visited = set()

    while pq:
        cost, node, path = heapq.heappop(pq)

        if node in visited:
            continue
        visited.add(node)
        path = path + [node]

        if node == end:
            return path, cost

        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(pq, (cost + weight, neighbor, path))

    return None, None


def nodes_to_path(node_path):
    coords = []
    for node in node_path:
        lon, lat = get_node_coord(node)
        coords.append([lon, lat])
    return coords


def build_dynamic_route(start_port, end_port):
    graph = build_graph()
    node_path, total_distance = shortest_path(graph, start_port, end_port)

    if not node_path:
        return None, None, None

    route_points = nodes_to_path(node_path)
    return node_path, route_points, total_distance


def route_impacted(route_points, scenario):
    center_lon, center_lat = scenario["center"]
    radius_km = scenario["radius_km"]

    for lon, lat in route_points:
        if haversine_km(lon, lat, center_lon, center_lat) <= radius_km:
            return True
    return False


def build_route_df(route_points, impacted=False, reroute=False):
    return pd.DataFrame([
        {
            "name": "Rerouted Route" if reroute else "Simulated Route",
            "path": route_points,
            "color": [168, 85, 247] if reroute else ([220, 38, 38] if impacted else [37, 99, 235]),
        }
    ])


def build_scenario_df(selected_route_scenario):
    zone = SCENARIO_ZONES[selected_route_scenario]
    return pd.DataFrame([
        {
            "name": selected_route_scenario,
            "longitude": zone["center"][0],
            "latitude": zone["center"][1],
            "radius": zone["radius_km"] * 1000,
            "color": [245, 158, 11, 120],
            "impact": zone["impact"],
            "severity": zone["severity"],
        }
    ])


def build_port_points_df(start_port, end_port):
    return pd.DataFrame([
        {
            "name": start_port,
            "longitude": PORTS[start_port]["lon"],
            "latitude": PORTS[start_port]["lat"],
            "impact": "Route origin",
        },
        {
            "name": end_port,
            "longitude": PORTS[end_port]["lon"],
            "latitude": PORTS[end_port]["lat"],
            "impact": "Route destination",
        },
    ])


def render_route_simulator_map(route_df, scenario_df, ports_df, reroute_df=None):
    layers = []

    if not scenario_df.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=scenario_df,
                get_position='[longitude, latitude]',
                get_fill_color="color",
                get_radius="radius",
                pickable=True,
                opacity=0.35,
            )
        )

    layers.append(
        pdk.Layer(
            "PathLayer",
            data=route_df,
            get_path="path",
            get_color="color",
            width_scale=20,
            width_min_pixels=4,
            pickable=True,
        )
    )

    if reroute_df is not None and not reroute_df.empty:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=reroute_df,
                get_path="path",
                get_color="color",
                width_scale=20,
                width_min_pixels=4,
                pickable=True,
            )
        )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=ports_df,
            get_position='[longitude, latitude]',
            get_fill_color=[34, 197, 94, 220],
            get_radius=90000,
            pickable=True,
        )
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=20, longitude=20, zoom=1.4),
        map_style="light",
        tooltip={
            "html": "<b>{name}</b><br/>{impact}",
            "style": {"backgroundColor": "black", "color": "white"},
        },
    )

    st.pydeck_chart(deck, use_container_width=True)


def estimate_delay_days(selected_route_scenario, impacted):
    if not impacted or selected_route_scenario == "None":
        return 0

    delay_map = {
        "Strait of Hormuz Closure": "7–21 days",
        "Red Sea Disruption": "7–18 days",
        "Suez Canal Blockage": "10–20 days",
        "Panama Canal Restriction": "6–14 days",
        "Taiwan Strait Tension": "5–12 days",
        "Cape Diversion Pressure": "4–10 days",
        "South China Sea Tension": "5–15 days",
        "North Pacific Storm Corridor": "3–9 days",
    }
    return delay_map.get(selected_route_scenario, "3–10 days")


def get_reroute_points(start_port, end_port, selected_route_scenario):
    start = [PORTS[start_port]["lon"], PORTS[start_port]["lat"]]
    end = [PORTS[end_port]["lon"], PORTS[end_port]["lat"]]

    reroute_templates = {
        "Suez Canal Blockage": [start, [103.8519, 1.2903], [18.5, -34.0], end],
        "Red Sea Disruption": [start, [103.8519, 1.2903], [18.5, -34.0], end],
        "Panama Canal Restriction": [start, [-75.0, -55.0], end],
        "Taiwan Strait Tension": [start, [114.0, 12.0], [103.8519, 1.2903], end],
        "South China Sea Tension": [start, [135.0, 18.0], [95.0, 8.0], end],
        "North Pacific Storm Corridor": [start, [10.0, 0.0], [140.0, -15.0], end],
    }

    return reroute_templates.get(selected_route_scenario)


st.title("🌍 Supply Chain Risk Monitor")
st.caption(
    "Track global disruptions, upload a bill of materials, and identify exposed parts with sourcing recommendations."
)

top_left, top_right = st.columns([4, 1])
with top_right:
    if st.button("Refresh Live Events"):
        st.cache_data.clear()
        st.rerun()

st.sidebar.header("Controls")
uploaded_file = st.sidebar.file_uploader(
    "Upload BOM file",
    type=["csv", "xlsx", "xls"]
)

selected_scenario = st.sidebar.selectbox(
    "Scenario Simulator",
    options=["None"] + list(SCENARIOS.keys())
)

events_df = get_live_events()

if events_df.empty:
    st.warning("No live events were loaded. Check your event loaders and internet/API access.")

event_type_options = sorted(events_df["event_type"].dropna().unique().tolist()) if not events_df.empty else []
severity_options = sorted(events_df["severity"].dropna().unique().tolist()) if not events_df.empty else []

selected_event_types = st.sidebar.multiselect(
    "Filter by Event Type",
    options=event_type_options,
    default=event_type_options
)

selected_severity = st.sidebar.multiselect(
    "Filter by Severity",
    options=severity_options,
    default=severity_options
)

selected_risk_levels = st.sidebar.multiselect(
    "Filter by Risk Level",
    options=["High", "Medium", "Low"],
    default=["High", "Medium", "Low"]
)

st.sidebar.subheader("Route Simulator")

simulator_mode = st.sidebar.checkbox("Enable Route Simulator", value=False)

start_port = None
end_port = None
selected_route_scenario = "None"

if simulator_mode:
    port_names = sorted(PORTS.keys())
    start_port = st.sidebar.selectbox("Start Port", port_names, index=0, key="route_start_port")
    end_port = st.sidebar.selectbox("End Port", port_names, index=1, key="route_end_port")
    selected_route_scenario = st.sidebar.selectbox(
        "Route Scenario",
        ["None"] + list(SCENARIO_ZONES.keys()),
        key="route_scenario"
    )

if not events_df.empty:
    filtered_events = events_df[
        events_df["event_type"].isin(selected_event_types) &
        events_df["severity"].isin(selected_severity)
    ].copy()
else:
    filtered_events = pd.DataFrame()

filtered_events = apply_scenario(filtered_events, selected_scenario)

st.markdown("### Executive Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Live Events", len(filtered_events))
col2.metric("High Severity Events", int((filtered_events["severity"] == "High").sum()) if not filtered_events.empty else 0)
col3.metric("Countries Affected", filtered_events["country"].nunique() if not filtered_events.empty else 0)
col4.metric("Tracked Commodities", filtered_events["commodity"].nunique() if not filtered_events.empty else 0)
col5.metric("Live Feed Sources", filtered_events["source"].nunique() if not filtered_events.empty else 0)

legend_col1, legend_col2, legend_col3 = st.columns(3)
legend_col1.markdown("🟥 **High Risk / Conflict**")
legend_col2.markdown("🟨 **Medium Risk / Shipping / Sanctions**")
legend_col3.markdown("🟩 **Low Risk / General**")

ai_commentary = None
risk_df = pd.DataFrame()
filtered_risk_df = pd.DataFrame()

events_summary = {
    "live_events": int(len(filtered_events)),
    "high_severity_events": int((filtered_events["severity"] == "High").sum()) if not filtered_events.empty else 0,
    "top_countries": filtered_events["country"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "top_commodities": filtered_events["commodity"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "top_event_types": filtered_events["event_type"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "selected_scenario": selected_scenario,
}

st.divider()

left_col, right_col = st.columns([1.05, 1])

with left_col:
    st.subheader("Live Global Events")
    event_display_cols = [
        "event_type", "title", "country", "commodity", "severity", "source", "event_time"
    ]
    existing_cols = [col for col in event_display_cols if col in filtered_events.columns]

    if not filtered_events.empty and existing_cols:
        st.dataframe(filtered_events[existing_cols], use_container_width=True, hide_index=True)

        source_summary = (
            filtered_events.groupby("source")
            .size()
            .reset_index(name="event_count")
            .sort_values("event_count", ascending=False)
        )
        st.markdown("#### Event Source Mix")
        st.dataframe(source_summary, use_container_width=True, hide_index=True)

        if "url" in filtered_events.columns:
            st.markdown("#### Source Links")
            for _, row in filtered_events.head(10).iterrows():
                if pd.notna(row.get("url")) and row.get("url"):
                    st.markdown(f"- [{row['title']}]({row['url']})")
    else:
        st.info("No events match the current filters.")

    st.markdown("#### Timeline View")
    render_timeline(filtered_events)

with right_col:
    st.subheader("Live Risk Map")
    render_event_map(filtered_events)

    st.markdown("#### Regional Summary Panel")
    render_regional_summary(filtered_events)

st.divider()
st.subheader("BOM Risk Analysis")

if uploaded_file is not None:
    try:
        raw_bom_df = load_bom(uploaded_file)
        is_valid, missing_columns = validate_bom(raw_bom_df)

        if not is_valid:
            st.error("Missing required BOM columns: " + ", ".join(missing_columns))
            st.markdown("#### Required Minimum Columns")
            st.code("part_name, supplier_country")
        else:
            bom_df = clean_bom(raw_bom_df)

            bom_col1, bom_col2 = st.columns([1.3, 1])
            with bom_col1:
                st.success("BOM uploaded and validated successfully.")
                st.dataframe(bom_df, use_container_width=True, hide_index=True)

            with bom_col2:
                st.markdown("#### Uploaded BOM Summary")
                st.metric("Total Parts", len(bom_df))
                st.metric("Supplier Countries", bom_df["supplier_country"].nunique())
                if "commodity" in bom_df.columns:
                    tracked = bom_df["commodity"].replace("", pd.NA).dropna().nunique()
                    st.metric("Tracked BOM Commodities", tracked)

            risk_df = analyze_bom_risk(bom_df, filtered_events, home_country="United States")

            if not risk_df.empty:
                risk_df = add_recommendations(risk_df, bom_df)

                filtered_risk_df = risk_df[
                    risk_df["risk_level"].isin(selected_risk_levels)
                ].copy()

                st.subheader("Affected BOM Items")

                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("High Risk Parts", int((risk_df["risk_level"] == "High").sum()))
                rc2.metric("Medium Risk Parts", int((risk_df["risk_level"] == "Medium").sum()))
                rc3.metric("Low Risk Parts", int((risk_df["risk_level"] == "Low").sum()))

                display_cols = [
                    "part_number",
                    "part_name",
                    "commodity",
                    "supplier_country",
                    "matched_event",
                    "event_type",
                    "impacted_commodity",
                    "rule_trigger",
                    "risk_score",
                    "risk_level",
                ]
                existing_display_cols = [col for col in display_cols if col in filtered_risk_df.columns]

                st.dataframe(
                    filtered_risk_df[existing_display_cols],
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Detailed Risk Explanation")
                explanation_cols = [
                    "part_name",
                    "supplier_name",
                    "supplier_country",
                    "matched_event",
                    "risk_level",
                    "rule_trigger",
                    "inferred_commodities",
                    "reason",
                    "recommendation",
                ]
                explanation_cols = [col for col in explanation_cols if col in filtered_risk_df.columns]

                st.dataframe(
                    filtered_risk_df[explanation_cols],
                    use_container_width=True,
                    hide_index=True
                )

                csv_export = filtered_risk_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Risk Analysis Results",
                    data=csv_export,
                    file_name="risk_analysis_results.csv",
                    mime="text/csv"
                )
            else:
                st.info("No BOM items are directly affected by the current live events.")

    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("Upload a BOM file from the sidebar to begin analysis.")

    sample_bom = get_bom_template()
    st.markdown("#### Sample BOM Format")
    st.dataframe(sample_bom, use_container_width=True, hide_index=True)

    csv_data = sample_bom.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Sample BOM Template",
        data=csv_data,
        file_name="sample_bom_template.csv",
        mime="text/csv"
    )

bom_summary = {}
if not risk_df.empty:
    bom_summary = {
        "high_risk_parts": int((risk_df["risk_level"] == "High").sum()),
        "medium_risk_parts": int((risk_df["risk_level"] == "Medium").sum()),
        "top_impacted_countries": risk_df["supplier_country"].astype(str).value_counts().head(5).to_dict(),
        "top_impacted_commodities": risk_df["commodity"].astype(str).value_counts().head(5).to_dict(),
    }

try:
    if events_summary or bom_summary:
        with st.spinner("Generating AI risk commentary..."):
            ai_commentary = cached_ai_risk_commentary(
                json.dumps(events_summary, sort_keys=True),
                json.dumps(bom_summary, sort_keys=True),
            )
except Exception as e:
    st.warning(f"AI commentary unavailable: {e}")

if ai_commentary:
    st.divider()
    st.subheader("AI Risk Commentary")
    st.info(ai_commentary.get("executive_summary", "No commentary available."))
    st.write(f"**Urgency:** {ai_commentary.get('urgency', 'Unknown')}")
    st.write("**Top risks:**")
    for item in ai_commentary.get("top_risks", []):
        st.write(f"- {item}")
    st.write(f"**Recommended action:** {ai_commentary.get('recommended_action', 'No recommendation available.')}")

if not filtered_risk_df.empty:
    st.divider()
    st.subheader("AI Alternate Sourcing Prioritization")

    part_options = filtered_risk_df["part_name"].dropna().astype(str).tolist()
    if part_options:
        selected_part = st.selectbox("Select impacted part", options=part_options)

        selected_row = filtered_risk_df[filtered_risk_df["part_name"].astype(str) == selected_part].iloc[0]

        part_context = {
            "part_name": selected_row.get("part_name", ""),
            "commodity": selected_row.get("commodity", ""),
            "supplier_country": selected_row.get("supplier_country", ""),
            "risk_level": selected_row.get("risk_level", ""),
            "matched_event": selected_row.get("matched_event", ""),
            "event_type": selected_row.get("event_type", ""),
            "criticality": selected_row.get("criticality", ""),
            "current_supplier": selected_row.get("supplier_name", ""),
            "alternate_suppliers": [
                {
                    "supplier": selected_row.get("alternate_supplier", ""),
                    "country": selected_row.get("alternate_supplier_country", ""),
                }
            ],
        }

        try:
            with st.spinner("Ranking alternate suppliers with AI..."):
                alt_result = cached_ai_alternate_sources(
                    json.dumps(part_context, sort_keys=True)
                )

            st.write(f"**Best option:** {alt_result.get('best_option', 'N/A')}")
            for item in alt_result.get("ranking", []):
                st.write(f"{item.get('rank', '-')}. {item.get('supplier', 'Unknown')} — Score: {item.get('score', 'N/A')}")
                st.caption(item.get("reason", ""))
            st.write(f"**Switch recommendation:** {alt_result.get('switch_recommendation', 'No recommendation available.')}")
        except Exception as e:
            st.warning(f"AI alternate sourcing unavailable: {e}")

if selected_scenario != "None":
    st.divider()
    st.subheader("AI Scenario Assessment")

    scenario_context = {
        "scenario": selected_scenario,
        "visible_events": int(len(filtered_events)),
        "affected_commodities": filtered_events["commodity"].astype(str).value_counts().head(10).to_dict() if not filtered_events.empty else {},
        "affected_countries": filtered_events["country"].astype(str).value_counts().head(10).to_dict() if not filtered_events.empty else {},
    }

    if not risk_df.empty:
        scenario_context["bom_exposure"] = {
            "high_risk_parts": int((risk_df["risk_level"] == "High").sum()),
            "medium_risk_parts": int((risk_df["risk_level"] == "Medium").sum()),
            "top_parts": risk_df["part_name"].astype(str).head(10).tolist(),
        }

    try:
        with st.spinner("Generating AI scenario assessment..."):
            scenario_ai = cached_ai_scenario_commentary(
                json.dumps(scenario_context, sort_keys=True)
            )

        st.write(f"**Summary:** {scenario_ai.get('scenario_summary', 'No summary available.')}")
        st.write(f"**Operational impact:** {scenario_ai.get('operational_impact', 'No operational impact available.')}")
        st.write(f"**Procurement impact:** {scenario_ai.get('procurement_impact', 'No procurement impact available.')}")
        st.write(f"**Recommended response:** {scenario_ai.get('recommended_response', 'No response available.')}")
    except Exception as e:
        st.warning(f"AI scenario analysis unavailable: {e}")

if simulator_mode and start_port and end_port:
    st.divider()
    st.subheader("Route Impact Simulator")

    if start_port == end_port:
        st.warning("Please select different start and end ports.")
    else:
        node_path, route_points, total_distance = build_dynamic_route(start_port, end_port)

        if not route_points:
            st.error("No route could be calculated for the selected ports.")
        else:
            impacted = False
            scenario_df = pd.DataFrame()
            reroute_df = pd.DataFrame()

            if selected_route_scenario != "None":
                scenario = SCENARIO_ZONES[selected_route_scenario]
                impacted = route_impacted(route_points, scenario)
                scenario_df = build_scenario_df(selected_route_scenario)

                reroute_points = get_reroute_points(start_port, end_port, selected_route_scenario)
                if impacted and reroute_points:
                    reroute_df = build_route_df(reroute_points, reroute=True)

            route_df = build_route_df(route_points, impacted=impacted)
            ports_df = build_port_points_df(start_port, end_port)

            render_route_simulator_map(
                route_df=route_df,
                scenario_df=scenario_df,
                ports_df=ports_df,
                reroute_df=reroute_df if not reroute_df.empty else None
            )

            sim_col1, sim_col2, sim_col3 = st.columns(3)
            sim_col1.metric("Estimated Route Distance", f"{total_distance:,.0f} km")
            sim_col2.metric("Scenario Selected", selected_route_scenario)
            sim_col3.metric("Impact Status", "Impacted" if impacted else "Clear")

            st.markdown("#### Calculated Maritime Path")
            st.code(" → ".join(node_path))

            if selected_route_scenario != "None":
                delay = estimate_delay_days(selected_route_scenario, impacted)

                if impacted:
                    st.error(f"This route is impacted by {selected_route_scenario}.")
                    st.write(f"**Expected Delay Impact:** {delay}")
                    st.write("**Likely Effect:** Higher transit-time risk, schedule volatility, and potential freight cost escalation.")
                    st.write("**Suggested Action:** Review alternate routing, rebalance safety stock, and evaluate backup sourcing.")

                    if not reroute_df.empty:
                        st.write("**Reroute Option Displayed:** A fallback detour path has been drawn in purple.")
                else:
                    st.success(f"This route is not directly impacted by {selected_route_scenario}.")
                    st.write("**Expected Delay Impact:** None to limited direct impact based on current route geometry.")

            if selected_route_scenario != "None":
                route_scenario_context = {
                    "start_port": start_port,
                    "end_port": end_port,
                    "scenario": selected_route_scenario,
                    "route_impacted": impacted,
                    "route_nodes": node_path,
                    "estimated_distance_km": round(total_distance, 2),
                }

                try:
                    with st.spinner("Generating AI route impact assessment..."):
                        route_ai = cached_ai_scenario_commentary(
                            json.dumps(route_scenario_context, sort_keys=True)
                        )

                    st.markdown("#### AI Route Assessment")
                    st.write(f"**Summary:** {route_ai.get('scenario_summary', 'No summary available.')}")
                    st.write(f"**Operational impact:** {route_ai.get('operational_impact', 'No operational impact available.')}")
                    st.write(f"**Procurement impact:** {route_ai.get('procurement_impact', 'No procurement impact available.')}")
                    st.write(f"**Recommended response:** {route_ai.get('recommended_response', 'No response available.')}")
                except Exception as e:
                    st.warning(f"AI route assessment unavailable: {e}")

st.divider()
st.markdown(
    """
    **How it works:**  
    The platform monitors live disruption signals, maps affected geographies, compares them with supplier locations and commodities in the uploaded BOM, and highlights parts that may need sourcing action.  
    AI then interprets the event landscape, summarizes major risks, ranks alternate sourcing paths, evaluates disruption scenarios, and simulates route exposure across major maritime corridors.
    """
)
