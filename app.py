import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.resolve()))

import streamlit as st
import pandas as pd
import pydeck as pdk

from utils.bom_parser import load_bom, validate_bom, clean_bom, get_bom_template
from utils.risk_engine import analyze_bom_risk
from utils.recommender import add_recommendations
from utils.event_loader import load_all_events


st.set_page_config(
    page_title="Supply Chain Risk Monitor",
    page_icon="🌍",
    layout="wide"
)


@st.cache_data(ttl=900)
def get_live_events() -> pd.DataFrame:
    return load_all_events()


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

with right_col:
    st.subheader("Live Risk Map")
    render_event_map(filtered_events)

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

st.divider()
st.markdown(
    """
    **How it works:**  
    The platform monitors live disruption signals, maps affected geographies, compares them with supplier locations and commodities in the uploaded BOM, and highlights parts that may need sourcing action.
    """
)
