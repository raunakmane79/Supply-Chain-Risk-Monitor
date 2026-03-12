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

    color_map = {
        "High": [220, 38, 38, 180],
        "Medium": [245, 158, 11, 180],
        "Low": [34, 197, 94, 180],
    }

    radius_map = {
        "High": 120000,
        "Medium": 80000,
        "Low": 50000,
    }

    df["color"] = df["severity"].map(color_map).apply(
        lambda x: x if isinstance(x, list) else [100, 100, 255, 160]
    )
    df["radius"] = df["severity"].map(radius_map).fillna(60000)

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


def style_risk_table(df: pd.DataFrame):
    if df.empty:
        return df
    return df.style.applymap(
        lambda x: (
            "background-color: #fee2e2; color: #991b1b; font-weight: 600"
            if x == "High"
            else "background-color: #fef3c7; color: #92400e; font-weight: 600"
            if x == "Medium"
            else "background-color: #dcfce7; color: #166534; font-weight: 600"
            if x == "Low"
            else ""
        ),
        subset=["risk_level"]
    )


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

event_type_options = sorted(events_df["event_type"].dropna().unique().tolist())
severity_options = sorted(events_df["severity"].dropna().unique().tolist())

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

filtered_events = events_df[
    events_df["event_type"].isin(selected_event_types) &
    events_df["severity"].isin(selected_severity)
].copy()

st.markdown("### Executive Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Live Events", len(filtered_events))
col2.metric("High Severity Events", int((filtered_events["severity"] == "High").sum()))
col3.metric("Countries Affected", filtered_events["country"].nunique())
col4.metric("Tracked Commodities", filtered_events["commodity"].nunique())
col5.metric("Live Feed Sources", filtered_events["source"].nunique())

legend_col1, legend_col2, legend_col3 = st.columns(3)
legend_col1.markdown("🟥 **High Risk / High Severity**")
legend_col2.markdown("🟨 **Medium Risk / Medium Severity**")
legend_col3.markdown("🟩 **Low Risk / Low Severity**")

st.divider()

left_col, right_col = st.columns([1.05, 1])

with left_col:
    st.subheader("Live Global Events")
    event_display_cols = [
        "event_type", "title", "country", "commodity", "severity", "source", "event_time"
    ]
    existing_cols = [col for col in event_display_cols if col in filtered_events.columns]
    st.dataframe(filtered_events[existing_cols], use_container_width=True, hide_index=True)
    
    source_summary = (
        filtered_events.groupby("source")
        .size()
        .reset_index(name="event_count")
        .sort_values("event_count", ascending=False)
    )
    st.markdown("#### Event Source Mix")
    st.dataframe(source_summary, use_container_width=True, hide_index=True)

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
                    st.metric("Tracked BOM Commodities", bom_df["commodity"].replace("", pd.NA).dropna().nunique())

            risk_df = analyze_bom_risk(bom_df, filtered_events)

            if not risk_df.empty:
                risk_df = add_recommendations(risk_df, bom_df)
                filtered_risk_df = risk_df[risk_df["risk_level"].isin(selected_risk_levels)].copy()

                st.divider()
                st.subheader("Affected BOM Items")

                high_risk_count = int((risk_df["risk_level"] == "High").sum())
                medium_risk_count = int((risk_df["risk_level"] == "Medium").sum())
                low_risk_count = int((risk_df["risk_level"] == "Low").sum())

                c1, c2, c3 = st.columns(3)
                c1.metric("High Risk Parts", high_risk_count)
                c2.metric("Medium Risk Parts", medium_risk_count)
                c3.metric("Low Risk Parts", low_risk_count)

                display_cols = [
                    "part_number",
                    "part_name",
                    "commodity",
                    "supplier_country",
                    "matched_event",
                    "event_type",
                    "impacted_commodity",
                    "risk_score",
                    "risk_level",
                ]
                existing_display_cols = [col for col in display_cols if col in filtered_risk_df.columns]

                st.dataframe(
                    style_risk_table(filtered_risk_df[existing_display_cols]),
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Priority Recommendations")
                priority_df = filtered_risk_df[
                    filtered_risk_df["risk_level"].isin(["High", "Medium"])
                ].copy()

                if not priority_df.empty:
                    st.dataframe(
                        priority_df[
                            [
                                "part_name",
                                "supplier_country",
                                "risk_level",
                                "matched_event",
                                "recommendation",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No high or medium risk parts under current filters.")

                st.subheader("Detailed Risk Explanation")
                st.dataframe(
                    filtered_risk_df[
                        [
                            "part_name",
                            "supplier_name",
                            "supplier_country",
                            "matched_event",
                            "risk_level",
                            "reason",
                            "recommendation",
                        ]
                    ],
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
