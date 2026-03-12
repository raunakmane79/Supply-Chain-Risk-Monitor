import sys
from pathlib import Path
import json

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
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
    df = df.dropna(subset=["event_time"])

    if df.empty:
        st.info("No valid event times available.")
        return

    df["hour_bucket"] = df["event_time"].dt.floor("h")
    timeline = df.groupby("hour_bucket").size().reset_index(name="event_count")
    st.line_chart(timeline.set_index("hour_bucket"))


REGION_MAP = {
    "China": "Asia",
    "Taiwan": "Asia",
    "Japan": "Asia",
    "India": "Asia",
    "South Korea": "Asia",
    "Singapore": "Asia",
    "Vietnam": "Asia",
    "Iran": "Middle East",
    "Israel": "Middle East",
    "Egypt": "Middle East",
    "Yemen": "Middle East",
    "Ukraine": "Europe",
    "Russia": "Europe",
    "Germany": "Europe",
    "Chile": "South America",
    "Brazil": "South America",
    "Peru": "South America",
    "United States": "North America",
    "Canada": "North America",
    "Mexico": "North America",
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

st.divider()
st.markdown(
    """
    **How it works:**  
    The platform monitors live disruption signals, maps affected geographies, compares them with supplier locations and commodities in the uploaded BOM, and highlights parts that may need sourcing action.  
    AI then interprets the event landscape, summarizes major risks, ranks alternate sourcing paths, and evaluates disruption scenarios.
    """
)
