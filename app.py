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
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
st.markdown(
    """
    <style>
    :root {
        --bg: #f6f8fb;
        --panel: rgba(255,255,255,0.82);
        --panel-solid: #ffffff;
        --line: rgba(15, 23, 42, 0.08);
        --line-strong: rgba(15, 23, 42, 0.14);
        --text: #0f172a;
        --muted: #64748b;

        --sidebar-bg-1: #07111f;
        --sidebar-bg-2: #0b1730;
        --sidebar-surface: rgba(255,255,255,0.05);
        --sidebar-surface-2: rgba(255,255,255,0.07);
        --sidebar-border: rgba(255,255,255,0.10);
        --sidebar-text: #f8fafc;
        --sidebar-muted: rgba(241,245,249,0.72);

        --blue: #2563eb;
        --blue-soft: rgba(37, 99, 235, 0.10);
        --red: #dc2626;
        --red-soft: rgba(220, 38, 38, 0.12);
        --amber: #d97706;
        --amber-soft: rgba(217, 119, 6, 0.12);
        --green: #16a34a;
        --green-soft: rgba(22, 163, 74, 0.12);

        --shadow-sm: 0 8px 24px rgba(15, 23, 42, 0.05);
        --shadow-md: 0 18px 50px rgba(15, 23, 42, 0.08);
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37,99,235,0.06), transparent 25%),
            radial-gradient(circle at top right, rgba(15,23,42,0.05), transparent 22%),
            var(--bg);
        color: var(--text);
    }

    .block-container {
        max-width: 1520px;
        padding-top: 1.05rem;
        padding-bottom: 2rem;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
    }

    h1, h2, h3, h4 {
        color: var(--text);
        letter-spacing: -0.03em;
    }

    /* MAIN APP ONLY */
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] div,
    [data-testid="stAppViewContainer"] span {
        color: inherit;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-bg-1) 0%, var(--sidebar-bg-2) 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }

    [data-testid="stSidebar"] * {
        color: var(--sidebar-text);
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--sidebar-muted) !important;
    }

    /* Sidebar section cards / expanders */
    [data-testid="stSidebar"] .stExpander {
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.03));
        border: 1px solid var(--sidebar-border);
        border-radius: 20px;
        overflow: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        margin-bottom: 0.9rem;
    }

    [data-testid="stSidebar"] .stExpander details {
        background: transparent !important;
    }

    [data-testid="stSidebar"] .stExpander summary {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
        color: var(--sidebar-text) !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] .stExpander details > div {
        background: transparent !important;
        padding-top: 0.25rem;
    }

    /* Labels */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stText,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stFileUploader label,
    [data-testid="stSidebar"] .stCheckbox label {
        color: var(--sidebar-text) !important;
        font-weight: 600 !important;
    }

    /* Inputs */
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stNumberInput input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid var(--sidebar-border) !important;
        color: var(--sidebar-text) !important;
        border-radius: 14px !important;
        min-height: 48px !important;
        box-shadow: none !important;
    }

    /* Multiselect tags */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: rgba(239, 68, 68, 0.16) !important;
        border: 1px solid rgba(239, 68, 68, 0.26) !important;
        color: #fecaca !important;
        border-radius: 10px !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] span,
    [data-testid="stSidebar"] [data-baseweb="tag"] svg {
        color: #fee2e2 !important;
        fill: #fee2e2 !important;
    }

    /* File uploader */
    [data-testid="stSidebar"] .stFileUploader > div {
        width: 100%;
    }

    [data-testid="stSidebar"] .stFileUploader section {
        background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.04)) !important;
        border: 1px dashed rgba(255,255,255,0.16) !important;
        border-radius: 18px !important;
        padding: 1rem !important;
    }

    [data-testid="stSidebar"] .stFileUploader section:hover {
        border-color: rgba(255,255,255,0.24) !important;
        background: rgba(255,255,255,0.07) !important;
    }

    [data-testid="stSidebar"] .stFileUploader small,
    [data-testid="stSidebar"] .stFileUploader span,
    [data-testid="stSidebar"] .stFileUploader p {
        color: var(--sidebar-muted) !important;
    }

    [data-testid="stSidebar"] .stFileUploader button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 0 !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.45rem 0.9rem !important;
    }

    /* Buttons */
    [data-testid="stSidebar"] .stButton button,
    [data-testid="stSidebar"] .stDownloadButton button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 0 !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        min-height: 48px;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .stButton button:hover,
    [data-testid="stSidebar"] .stDownloadButton button:hover {
        background: #f8fafc !important;
    }

    /* Divider */
    [data-testid="stSidebar"] hr {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.08);
        margin: 1rem 0;
    }

    /* MAIN CONTENT CARDS */
    .top-shell {
        margin-bottom: 1rem;
    }

    .hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.86), rgba(255,255,255,0.72));
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.58);
        box-shadow: var(--shadow-md);
        border-radius: 28px;
        padding: 1.5rem 1.5rem 1.35rem 1.5rem;
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
    }

    .hero::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(120deg, rgba(37,99,235,0.10), transparent 45%, rgba(15,23,42,0.05));
        pointer-events: none;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.38rem 0.72rem;
        border-radius: 999px;
        background: var(--blue-soft);
        color: var(--blue);
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: 1.45fr 0.85fr;
        gap: 1rem;
        position: relative;
        z-index: 1;
    }

    .hero-title {
        font-size: 2.35rem;
        line-height: 1.02;
        font-weight: 800;
        margin: 0 0 0.6rem 0;
    }

    .hero-subtitle {
        font-size: 1rem;
        line-height: 1.7;
        color: var(--muted);
        max-width: 760px;
    }

    .hero-kicker {
        display: grid;
        grid-template-columns: repeat(2, minmax(0,1fr));
        gap: 0.8rem;
    }

    .hero-mini {
        background: rgba(15,23,42,0.04);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 18px;
        padding: 0.95rem 1rem;
    }

    .hero-mini-label {
        font-size: 0.78rem;
        color: var(--muted);
        margin-bottom: 0.3rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .hero-mini-value {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text);
    }

    .shell-card {
        background: rgba(255,255,255,0.84);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.68);
        border-radius: 24px;
        padding: 1rem 1rem 1.05rem 1rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 1rem;
    }

    .section-heading {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.9rem;
    }

    .section-title {
        font-size: 1.08rem;
        font-weight: 750;
        color: var(--text);
        letter-spacing: -0.02em;
    }

    .section-caption {
        font-size: 0.92rem;
        color: var(--muted);
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 0.9rem 0.95rem;
        box-shadow: none;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--muted);
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: var(--text);
        font-weight: 800;
        letter-spacing: -0.03em;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.25rem;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        border-radius: 999px;
        padding: 0.48rem 0.82rem;
        font-size: 0.82rem;
        font-weight: 700;
        border: 1px solid transparent;
    }

    .pill.high {
        background: var(--red-soft);
        color: var(--red);
        border-color: rgba(220,38,38,0.18);
    }

    .pill.medium {
        background: var(--amber-soft);
        color: var(--amber);
        border-color: rgba(217,119,6,0.18);
    }

    .pill.low {
        background: var(--green-soft);
        color: var(--green);
        border-color: rgba(22,163,74,0.16);
    }

    .note-strip {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.9rem 1rem;
        border-radius: 18px;
        background: linear-gradient(90deg, rgba(37,99,235,0.08), rgba(255,255,255,0.35));
        border: 1px solid rgba(37,99,235,0.12);
        color: var(--muted);
        margin-top: 0.2rem;
    }

    .insight {
        border-radius: 20px;
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.72);
        padding: 1rem;
        margin-bottom: 0.75rem;
    }

    .insight.high {
        border-left: 4px solid var(--red);
    }

    .insight.medium {
        border-left: 4px solid var(--amber);
    }

    .insight.low {
        border-left: 4px solid var(--green);
    }

    .insight-title {
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .muted {
        color: var(--muted);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 0.45rem 0.85rem;
        color: #334155;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: #0f172a !important;
        color: white !important;
        border-color: #0f172a !important;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 20px;
        overflow: hidden;
        background: rgba(255,255,255,0.92);
    }

    .stButton button,
    .stDownloadButton button {
        background: #0f172a;
        color: white;
        border: 0;
        border-radius: 14px;
        padding: 0.64rem 1rem;
        font-weight: 700;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        background: #111f38;
        color: white;
    }

    hr {
        border: none;
        border-top: 1px solid var(--line);
        margin: 1rem 0 1.2rem 0;
    }

    @media (max-width: 1100px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
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
    ("Shanghai", "EastChinaSea"), ("Shenzhen", "SouthChinaSea"), ("Hong Kong", "SouthChinaSea"),
    ("Busan", "SeaOfJapan"), ("Kaohsiung", "TaiwanStrait"), ("Tokyo", "EastChinaSea"),
    ("Manila", "PhilippineSea"), ("Jakarta", "JavaSea"), ("Singapore", "Malacca"),
    ("Mumbai", "ArabianSea"), ("Chennai", "BayOfBengal"), ("Dubai", "Hormuz"),
    ("Dammam", "Hormuz"), ("Jeddah", "RedSea"), ("Rotterdam", "NorthSea"),
    ("Hamburg", "NorthSea"), ("Antwerp", "NorthSea"), ("Valencia", "MediterraneanWest"),
    ("Piraeus", "MediterraneanEast"), ("London", "NorthSea"), ("Los Angeles", "NorthPacificEast"),
    ("Long Beach", "NorthPacificEast"), ("Vancouver", "NorthPacificEast"), ("Houston", "PanamaCanal"),
    ("New York", "NorthAtlantic"), ("Savannah", "NorthAtlantic"), ("Panama City", "PanamaCanal"),
    ("Santos", "SouthAtlantic"), ("Callao", "SouthPacificMid"), ("Buenos Aires", "SouthAtlantic"),
    ("Durban", "CapeOfGoodHope"), ("Cape Town", "CapeOfGoodHope"), ("Mombasa", "EastAfrica"),
    ("Lagos", "WestAfrica"), ("Sydney", "TasmanSea"), ("Melbourne", "TasmanSea"),
    ("SeaOfJapan", "EastChinaSea"), ("EastChinaSea", "TaiwanStrait"), ("EastChinaSea", "NorthPacificWest"),
    ("TaiwanStrait", "SouthChinaSea"), ("TaiwanStrait", "PhilippineSea"), ("SouthChinaSea", "Malacca"),
    ("SouthChinaSea", "PhilippineSea"), ("PhilippineSea", "NorthPacificWest"), ("NorthPacificWest", "PacificMid"),
    ("NorthPacificEast", "PacificMid"), ("PacificMid", "NorthPacificEast"), ("JavaSea", "Malacca"),
    ("JavaSea", "TimorSea"), ("TimorSea", "IndianOceanEast"), ("TasmanSea", "SouthPacificMid"),
    ("Malacca", "IndianOceanEast"), ("BayOfBengal", "Malacca"), ("BayOfBengal", "IndianOceanMid"),
    ("IndianOceanEast", "IndianOceanMid"), ("IndianOceanMid", "ArabianSea"), ("IndianOceanMid", "CapeOfGoodHope"),
    ("ArabianSea", "Hormuz"), ("ArabianSea", "GulfOfAden"), ("EastAfrica", "GulfOfAden"),
    ("EastAfrica", "CapeOfGoodHope"), ("GulfOfAden", "RedSea"), ("RedSea", "Suez"),
    ("Suez", "MediterraneanEast"), ("MediterraneanEast", "MediterraneanCentral"),
    ("MediterraneanCentral", "MediterraneanWest"), ("MediterraneanWest", "Gibraltar"),
    ("Gibraltar", "NorthSea"), ("Gibraltar", "NorthAtlantic"), ("Gibraltar", "WestAfrica"),
    ("WestAfrica", "SouthAtlantic"), ("CapeOfGoodHope", "SouthAtlantic"), ("SouthAtlantic", "NorthAtlantic"),
    ("SouthAtlantic", "PanamaCanal"), ("PanamaCanal", "SouthPacificMid"), ("PanamaCanal", "NorthPacificEast"),
    ("NorthAtlantic", "NorthSea"),
]

SCENARIO_ZONES = {
    "Strait of Hormuz Closure": {"center": [56.25, 26.5667], "radius_km": 450, "severity": "High", "impact": "Oil, LNG, Middle East shipping"},
    "Red Sea Disruption": {"center": [38.0, 20.0], "radius_km": 900, "severity": "High", "impact": "Asia-Europe shipping"},
    "Suez Canal Blockage": {"center": [32.5498, 29.9668], "radius_km": 250, "severity": "High", "impact": "Europe-Asia maritime corridor"},
    "Panama Canal Restriction": {"center": [-79.68, 9.08], "radius_km": 250, "severity": "High", "impact": "Atlantic-Pacific flows"},
    "Taiwan Strait Tension": {"center": [119.5, 24.0], "radius_km": 500, "severity": "High", "impact": "Semiconductor and East Asia shipping"},
    "Cape Diversion Pressure": {"center": [18.5, -34.0], "radius_km": 500, "severity": "Medium", "impact": "Long-route diversion stress"},
    "South China Sea Tension": {"center": [114.0, 12.0], "radius_km": 800, "severity": "High", "impact": "Asia intra-regional trade and electronics flows"},
    "North Pacific Storm Corridor": {"center": [-160.0, 25.0], "radius_km": 1200, "severity": "Medium", "impact": "Trans-Pacific shipping delays"},
}


@st.cache_data(ttl=900)
def get_live_events() -> pd.DataFrame:
    return load_all_events()


@st.cache_data(ttl=900, show_spinner=False)
def cached_ai_risk_commentary(events_summary_json: str, bom_summary_json: str):
    return generate_ai_risk_commentary(json.loads(events_summary_json), json.loads(bom_summary_json))


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
    return synthetic if events_df.empty else pd.concat([events_df, synthetic], ignore_index=True)


def add_map_styles(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.copy()

    def pick_color(row):
        event_type = row.get("event_type", "")
        severity = row.get("severity", "")
        if event_type == "Conflict":
            return [220, 38, 38, 210]
        if event_type == "Sanctions":
            return [217, 119, 6, 210]
        if event_type == "Shipping Disruption":
            return [37, 99, 235, 210]
        if severity == "High":
            return [220, 38, 38, 185]
        if severity == "Medium":
            return [217, 119, 6, 185]
        return [22, 163, 74, 185]

    def pick_radius(row):
        severity = row.get("severity", "")
        if severity == "High":
            return 150000
        if severity == "Medium":
            return 100000
        return 70000

    df["color"] = df.apply(pick_color, axis=1)
    df["radius"] = df.apply(pick_radius, axis=1)
    return df


def render_event_map(events_df: pd.DataFrame):
    if events_df.empty:
        st.info("No events available for map display.")
        return

    map_df = add_map_styles(events_df)

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[longitude, latitude]',
            get_fill_color="color",
            get_radius="radius",
            pickable=True,
            opacity=0.82,
            stroked=True,
            filled=True,
            radius_min_pixels=7,
            radius_max_pixels=34,
            line_width_min_pixels=1,
        )
    ]

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=20, longitude=0, zoom=1.12, pitch=0),
        tooltip={
            "html": "<b>{title}</b><br/>{event_type} · {severity}<br/>{country}<br/>Commodity: {commodity}<br/>Source: {source}",
            "style": {"backgroundColor": "#0f172a", "color": "white", "borderRadius": "12px"},
        },
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
    st.line_chart(timeline.set_index("hour_bucket"), use_container_width=True)


REGION_MAP = {
    "China": "Asia", "Taiwan": "Asia", "Japan": "Asia", "India": "Asia", "South Korea": "Asia",
    "Singapore": "Asia", "Vietnam": "Asia", "Philippines": "Asia", "Indonesia": "Asia",
    "Iran": "Middle East", "Israel": "Middle East", "Egypt": "Middle East", "Yemen": "Middle East",
    "Saudi Arabia": "Middle East", "UAE": "Middle East", "Ukraine": "Europe", "Russia": "Europe",
    "Germany": "Europe", "Netherlands": "Europe", "Belgium": "Europe", "Chile": "South America",
    "Brazil": "South America", "Peru": "South America", "Argentina": "South America",
    "United States": "North America", "Canada": "North America", "Mexico": "North America",
    "South Africa": "Africa", "Kenya": "Africa", "Nigeria": "Africa", "Australia": "Oceania",
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
        .agg(live_events=("title", "count"), countries=("country", "nunique"))
        .reset_index()
        .sort_values("live_events", ascending=False)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
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
    return [[get_node_coord(node)[0], get_node_coord(node)[1]] for node in node_path]


def build_dynamic_route(start_port, end_port):
    graph = build_graph()
    node_path, total_distance = shortest_path(graph, start_port, end_port)
    if not node_path:
        return None, None, None
    return node_path, nodes_to_path(node_path), total_distance


def route_impacted(route_points, scenario):
    center_lon, center_lat = scenario["center"]
    radius_km = scenario["radius_km"]
    return any(haversine_km(lon, lat, center_lon, center_lat) <= radius_km for lon, lat in route_points)


def build_route_df(route_points, impacted=False, reroute=False):
    return pd.DataFrame([
        {
            "name": "Rerouted Route" if reroute else "Primary Route",
            "path": route_points,
            "color": [124, 58, 237] if reroute else ([220, 38, 38] if impacted else [15, 23, 42]),
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
            "color": [217, 119, 6, 110],
            "impact": zone["impact"],
            "severity": zone["severity"],
        }
    ])


def build_port_points_df(start_port, end_port):
    return pd.DataFrame([
        {"name": start_port, "longitude": PORTS[start_port]["lon"], "latitude": PORTS[start_port]["lat"], "impact": "Origin"},
        {"name": end_port, "longitude": PORTS[end_port]["lon"], "latitude": PORTS[end_port]["lat"], "impact": "Destination"},
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
                opacity=0.32,
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
            get_fill_color=[22, 163, 74, 220],
            get_radius=85000,
            pickable=True,
        )
    )
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=20, longitude=18, zoom=1.35),
        map_style="light",
        tooltip={"html": "<b>{name}</b><br/>{impact}", "style": {"backgroundColor": "#0f172a", "color": "white"}},
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


def render_priorities(filtered_risk_df: pd.DataFrame):
    if filtered_risk_df.empty:
        return
    st.markdown('<div class="section-heading"><div class="section-title">Immediate priorities</div><div class="section-caption">Most exposed items needing attention now</div></div>', unsafe_allow_html=True)
    for _, row in filtered_risk_df.head(3).iterrows():
        risk_class = str(row.get("risk_level", "Low")).lower()
        css = "high" if risk_class == "high" else "medium" if risk_class == "medium" else "low"
        st.markdown(
            f"""
            <div class="insight {css}">
                <div class="insight-title">{row.get('part_name', 'Unknown Part')}</div>
                <div class="muted">Supplier country: {row.get('supplier_country', 'Unknown')}</div>
                <div style="margin-top:0.35rem;">Trigger: {row.get('matched_event', 'N/A')}</div>
                <div style="margin-top:0.2rem;">Recommendation: {row.get('recommendation', 'Review sourcing options.')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.sidebar.markdown("## Control Center")
st.sidebar.markdown(
    '<div style="color: rgba(241,245,249,0.72); font-size: 0.96rem; line-height: 1.65; margin-bottom: 0.6rem;">'
    'Live monitoring, sourcing exposure, and route resilience in one workspace.'
    '</div>',
    unsafe_allow_html=True,
)

events_df = get_live_events()
if events_df.empty:
    st.warning("No live events were loaded. Check your event loaders and API/internet access.")

event_type_options = sorted(events_df["event_type"].dropna().unique().tolist()) if not events_df.empty else []
severity_options = sorted(events_df["severity"].dropna().unique().tolist()) if not events_df.empty else []

with st.sidebar.expander("Live updates", expanded=True):
    selected_scenario = st.selectbox("Scenario overlay", options=["None"] + list(SCENARIOS.keys()))
    selected_event_types = st.multiselect("Event type", options=event_type_options, default=event_type_options)
    selected_severity = st.multiselect("Severity", options=severity_options, default=severity_options)

with st.sidebar.expander("Upload BOM", expanded=True):
    uploaded_file = st.file_uploader("Upload BOM", type=["csv", "xlsx", "xls"])
    selected_risk_levels = st.multiselect("Risk level", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"])

with st.sidebar.expander("Route simulation", expanded=False):
    simulator_mode = st.checkbox("Enable route simulation", value=False)
    start_port = None
    end_port = None
    selected_route_scenario = "None"
    if simulator_mode:
        port_names = sorted(PORTS.keys())
        start_port = st.selectbox("Start port", port_names, index=0, key="route_start_port")
        end_port = st.selectbox("End port", port_names, index=1, key="route_end_port")
        selected_route_scenario = st.selectbox("Scenario", ["None"] + list(SCENARIO_ZONES.keys()), key="route_scenario")

st.sidebar.markdown("---")
if st.sidebar.button("Refresh live events", use_container_width=True, type="primary"):    st.cache_data.clear()
    st.rerun()


# Data preparation
if not events_df.empty:
    filtered_events = events_df[
        events_df["event_type"].isin(selected_event_types) & events_df["severity"].isin(selected_severity)
    ].copy()
else:
    filtered_events = pd.DataFrame()

filtered_events = apply_scenario(filtered_events, selected_scenario)

live_count = len(filtered_events)
high_count = int((filtered_events["severity"] == "High").sum()) if not filtered_events.empty else 0
country_count = filtered_events["country"].nunique() if not filtered_events.empty else 0
commodity_count = filtered_events["commodity"].nunique() if not filtered_events.empty else 0
source_count = filtered_events["source"].nunique() if not filtered_events.empty else 0


# Hero / landing section
st.markdown(
    f"""
    <div class="top-shell">
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">Executive risk intelligence</div>
                    <div class="hero-title">See disruption exposure before it becomes an operations problem.</div>
                    <div class="hero-subtitle">
                        A decision-grade command center for live event monitoring, supplier exposure analysis,
                        and route-level disruption simulation. Built for fast executive review and action.
                    </div>
                </div>
                <div class="hero-kicker">
                    <div class="hero-mini">
                        <div class="hero-mini-label">Live events</div>
                        <div class="hero-mini-value">{live_count}</div>
                    </div>
                    <div class="hero-mini">
                        <div class="hero-mini-label">High severity</div>
                        <div class="hero-mini-value">{high_count}</div>
                    </div>
                    <div class="hero-mini">
                        <div class="hero-mini-label">Countries affected</div>
                        <div class="hero-mini-value">{country_count}</div>
                    </div>
                    <div class="hero-mini">
                        <div class="hero-mini-label">Tracked commodities</div>
                        <div class="hero-mini-value">{commodity_count}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.45, 0.92], gap="large")

with left:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-heading"><div><div class="section-title">Global risk map</div><div class="section-caption">Live disruption clusters with severity-weighted markers</div></div></div>',
        unsafe_allow_html=True,
    )
    render_event_map(filtered_events)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-heading"><div><div class="section-title">Live updates</div><div class="section-caption">Current market and supply risk footprint</div></div></div>',
        unsafe_allow_html=True,
    )

    k1, k2 = st.columns(2)
    with k1:
        st.metric("Sources", source_count)
    with k2:
        st.metric("Scenario", selected_scenario if selected_scenario != "None" else "Base")

    st.markdown(
        """
        <div class="pill-row">
            <span class="pill high">High risk / conflict</span>
            <span class="pill medium">Shipping / sanctions</span>
            <span class="pill low">Low risk / general</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not filtered_events.empty:
        preview_cols = [c for c in ["title", "event_type", "country", "severity", "source"] if c in filtered_events.columns]
        preview_df = filtered_events[preview_cols].head(8)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)
    else:
        st.info("No live events match the current filters.")

    st.markdown(
        """
        <div class="note-strip">
            <div>Use the left sidebar to change event filters, upload a BOM, and test route resilience scenarios.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


# Executive metrics
st.markdown('<div class="shell-card">', unsafe_allow_html=True)
st.markdown(
    '<div class="section-heading"><div><div class="section-title">Executive snapshot</div><div class="section-caption">High-level monitoring metrics for leadership review</div></div></div>',
    unsafe_allow_html=True,
)
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Live Events", live_count)
mc2.metric("High Severity", high_count)
mc3.metric("Countries", country_count)
mc4.metric("Commodities", commodity_count)
mc5.metric("Sources", source_count)
st.markdown("</div>", unsafe_allow_html=True)


ai_commentary = None
risk_df = pd.DataFrame()
filtered_risk_df = pd.DataFrame()

events_summary = {
    "live_events": int(live_count),
    "high_severity_events": int(high_count),
    "top_countries": filtered_events["country"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "top_commodities": filtered_events["commodity"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "top_event_types": filtered_events["event_type"].astype(str).value_counts().head(5).to_dict() if not filtered_events.empty else {},
    "selected_scenario": selected_scenario,
}

tab1, tab2, tab3, tab4 = st.tabs(["Live feed", "Trend view", "BOM exposure", "Route intelligence"])

with tab1:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading"><div><div class="section-title">Event stream</div><div class="section-caption">Filtered live incidents and source mix</div></div></div>', unsafe_allow_html=True)
    event_display_cols = ["event_type", "title", "country", "commodity", "severity", "source", "event_time"]
    existing_cols = [col for col in event_display_cols if col in filtered_events.columns]
    if not filtered_events.empty and existing_cols:
        st.dataframe(filtered_events[existing_cols], use_container_width=True, hide_index=True)
        source_summary = filtered_events.groupby("source").size().reset_index(name="event_count").sort_values("event_count", ascending=False)
        st.markdown("#### Source distribution")
        st.dataframe(source_summary, use_container_width=True, hide_index=True)
    else:
        st.info("No events match the active filters.")
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    c1, c2 = st.columns([1.15, 0.85], gap="large")
    with c1:
        st.markdown('<div class="shell-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-heading"><div><div class="section-title">Timeline</div><div class="section-caption">Velocity of event flow over time</div></div></div>', unsafe_allow_html=True)
        render_timeline(filtered_events)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="shell-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-heading"><div><div class="section-title">Regional distribution</div><div class="section-caption">Where current disruption is concentrated</div></div></div>', unsafe_allow_html=True)
        render_regional_summary(filtered_events)
        st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading"><div><div class="section-title">BOM exposure analysis</div><div class="section-caption">Upload a BOM to assess supplier and commodity risk</div></div></div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        try:
            raw_bom_df = load_bom(uploaded_file)
            is_valid, missing_columns = validate_bom(raw_bom_df)
            if not is_valid:
                st.error("Missing required BOM columns: " + ", ".join(missing_columns))
                st.code("part_name, supplier_country")
            else:
                bom_df = clean_bom(raw_bom_df)
                st.markdown('<div class="note-strip">BOM validated successfully. Review part exposure, priority actions, and export the result for sourcing decisions.</div>', unsafe_allow_html=True)

                b1, b2 = st.columns([1.25, 0.75], gap="large")
                with b1:
                    st.dataframe(bom_df, use_container_width=True, hide_index=True)
                with b2:
                    st.metric("Total parts", len(bom_df))
                    st.metric("Supplier countries", bom_df["supplier_country"].nunique())
                    if "commodity" in bom_df.columns:
                        tracked = bom_df["commodity"].replace("", pd.NA).dropna().nunique()
                        st.metric("Tracked commodities", tracked)

                risk_df = analyze_bom_risk(bom_df, filtered_events, home_country="United States")
                if not risk_df.empty:
                    risk_df = add_recommendations(risk_df, bom_df)
                    filtered_risk_df = risk_df[risk_df["risk_level"].isin(selected_risk_levels)].copy()
                    if not filtered_risk_df.empty:
                        risk_order = {"High": 0, "Medium": 1, "Low": 2}
                        filtered_risk_df["risk_order"] = filtered_risk_df["risk_level"].map(risk_order).fillna(99)
                        sort_cols = ["risk_order"]
                        ascending = [True]
                        if "risk_score" in filtered_risk_df.columns:
                            sort_cols.append("risk_score")
                            ascending.append(False)
                        filtered_risk_df = filtered_risk_df.sort_values(sort_cols, ascending=ascending).drop(columns=["risk_order"])

                    r1, r2, r3 = st.columns(3)
                    r1.metric("High risk parts", int((risk_df["risk_level"] == "High").sum()))
                    r2.metric("Medium risk parts", int((risk_df["risk_level"] == "Medium").sum()))
                    r3.metric("Low risk parts", int((risk_df["risk_level"] == "Low").sum()))

                    render_priorities(filtered_risk_df)

                    st.markdown("#### Affected BOM items")
                    display_cols = ["part_number", "part_name", "commodity", "supplier_country", "matched_event", "event_type", "impacted_commodity", "rule_trigger", "risk_score", "risk_level"]
                    existing_display_cols = [col for col in display_cols if col in filtered_risk_df.columns]
                    if not filtered_risk_df.empty and existing_display_cols:
                        st.dataframe(filtered_risk_df[existing_display_cols], use_container_width=True, hide_index=True)

                    st.markdown("#### Detailed risk explanation")
                    explanation_cols = ["part_name", "supplier_name", "supplier_country", "matched_event", "risk_level", "rule_trigger", "inferred_commodities", "reason", "recommendation"]
                    explanation_cols = [col for col in explanation_cols if col in filtered_risk_df.columns]
                    if not filtered_risk_df.empty and explanation_cols:
                        st.dataframe(filtered_risk_df[explanation_cols], use_container_width=True, hide_index=True)

                    csv_export = filtered_risk_df.to_csv(index=False).encode("utf-8")
                    st.download_button("Download risk analysis", csv_export, "risk_analysis_results.csv", "text/csv")
                else:
                    st.info("No BOM items are directly affected under the current filters.")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    else:
        sample_bom = get_bom_template()
        st.info("Upload a BOM from the sidebar to run exposure analysis.")
        st.dataframe(sample_bom, use_container_width=True, hide_index=True)
        csv_data = sample_bom.to_csv(index=False).encode("utf-8")
        st.download_button("Download sample BOM template", csv_data, "sample_bom_template.csv", "text/csv")

    st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading"><div><div class="section-title">Route intelligence</div><div class="section-caption">Maritime path simulation with disruption overlays</div></div></div>', unsafe_allow_html=True)

    if simulator_mode and start_port and end_port:
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
                render_route_simulator_map(route_df, scenario_df, ports_df, reroute_df if not reroute_df.empty else None)

                s1, s2, s3 = st.columns(3)
                s1.metric("Estimated distance", f"{total_distance:,.0f} km")
                s2.metric("Scenario", selected_route_scenario)
                s3.metric("Status", "Impacted" if impacted else "Clear")

                st.code(" → ".join(node_path))
                if selected_route_scenario != "None":
                    delay = estimate_delay_days(selected_route_scenario, impacted)
                    if impacted:
                        st.error(f"This route is impacted by {selected_route_scenario}. Expected delay: {delay}")
                    else:
                        st.success("This route is not directly impacted by the selected scenario.")
    else:
        st.info("Enable route simulation from the sidebar to test global shipping paths.")
    st.markdown("</div>", unsafe_allow_html=True)


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
        with st.spinner("Generating AI commentary..."):
            ai_commentary = cached_ai_risk_commentary(json.dumps(events_summary, sort_keys=True), json.dumps(bom_summary, sort_keys=True))
except Exception as e:
    st.warning(f"AI commentary unavailable: {e}")

if ai_commentary:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading"><div><div class="section-title">AI commentary</div><div class="section-caption">Condensed decision support for leadership</div></div></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="insight high">
            <div class="insight-title">Executive summary</div>
            <div>{ai_commentary.get('executive_summary', 'No commentary available.')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    a1, a2 = st.columns([0.7, 1.3], gap="large")
    with a1:
        st.metric("Urgency", ai_commentary.get("urgency", "Unknown"))
    with a2:
        st.markdown(
            f"""
            <div class="insight medium">
                <div class="insight-title">Recommended action</div>
                <div>{ai_commentary.get('recommended_action', 'No recommendation available.')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if ai_commentary.get("top_risks"):
        st.markdown("#### Top risks")
        for item in ai_commentary.get("top_risks", []):
            st.markdown(f'<div class="insight medium">{item}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="shell-card">', unsafe_allow_html=True)
st.markdown('<div class="section-heading"><div><div class="section-title">Platform logic</div><div class="section-caption">How the workspace converts signals into action</div></div></div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="muted" style="line-height:1.85;">
        1. Ingest live disruption signals by geography, commodity, and severity.<br>
        2. Match those signals against supplier countries and BOM attributes.<br>
        3. Surface the most exposed parts and suggested sourcing responses.<br>
        4. Simulate route-level impact to support logistics and procurement decisions.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
