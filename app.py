import streamlit as st
import pandas as pd
import pydeck as pdk

from utils.bom_parser import load_bom, validate_bom, clean_bom, get_bom_template
from utils.risk_engine import analyze_bom_risk
from utils.recommender import add_recommendations


st.set_page_config(
    page_title="Supply Chain Risk Monitor",
    page_icon="🌍",
    layout="wide"
)


def load_sample_events() -> pd.DataFrame:
    data = [
        {
            "event_type": "Earthquake",
            "title": "Major earthquake near Taiwan",
            "country": "Taiwan",
            "commodity": "Semiconductor",
            "severity": "High",
            "latitude": 23.6978,
            "longitude": 120.9605,
        },
        {
            "event_type": "Flood",
            "title": "Flooding impacting port operations in China",
            "country": "China",
            "commodity": "Electronics",
            "severity": "Medium",
            "latitude": 31.2304,
            "longitude": 121.4737,
        },
        {
            "event_type": "Conflict",
            "title": "Conflict risk affecting metal shipments",
            "country": "Ukraine",
            "commodity": "Steel",
            "severity": "High",
            "latitude": 50.4501,
            "longitude": 30.5234,
        },
        {
            "event_type": "Storm",
            "title": "Storm disruption near Chile logistics corridor",
            "country": "Chile",
            "commodity": "Copper",
            "severity": "Medium",
            "latitude": -33.4489,
            "longitude": -70.6693,
        }
    ]
    return pd.DataFrame(data)


def add_map_styles(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.copy()

    color_map = {
        "High": [220, 38, 38, 180],     # red
        "Medium": [245, 158, 11, 180],  # amber
        "Low": [34, 197, 94, 180],      # green
    }

    radius_map = {
        "High": 120000,
        "Medium": 80000,
        "Low": 50000,
    }

    df["color"] = df["severity"].map(color_map)
    df["radius"] = df["severity"].map(radius_map)

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
        zoom=1.2,
        pitch=0,
    )

    tooltip = {
        "html": """
        <b>Event:</b> {title}<br/>
        <b>Type:</b> {event_type}<br/>
        <b>Country:</b> {country}<br/>
        <b>Commodity:</b> {commodity}<br/>
        <b>Severity:</b> {severity}
        """,
        "style": {
            "backgroundColor": "black",
            "color": "white"
        }
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/dark-v10",
    )

    st.pydeck_chart(deck, use_container_width=True)


st.title("🌍 AI-Inspired Supply Chain Risk Monitor")
st.markdown(
    """
    Monitor live global disruptions, upload a BOM, and identify which parts may be exposed
    based on supplier geography and commodity risk.
    """
)

# Sidebar
st.sidebar.header("Controls")
uploaded_file = st.sidebar.file_uploader(
    "Upload BOM file",
    type=["csv", "xlsx", "xls"]
)

selected_event_types = st.sidebar.multiselect(
    "Filter by Event Type",
    options=["Earthquake", "Flood", "Conflict", "Storm", "Wildfire", "Protest"],
    default=["Earthquake", "Flood", "Conflict", "Storm"]
)

selected_severity = st.sidebar.multiselect(
    "Filter by Severity",
    options=["High", "Medium", "Low"],
    default=["High", "Medium", "Low"]
)

selected_risk_levels = st.sidebar.multiselect(
    "Filter by Risk Level",
    options=["High", "Medium", "Low"],
    default=["High", "Medium", "Low"]
)

events_df = load_sample_events()

filtered_events = events_df[
    events_df["event_type"].isin(selected_event_types) &
    events_df["severity"].isin(selected_severity)
].copy()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Live Events", len(filtered_events))
col2.metric("High Severity Events", int((filtered_events["severity"] == "High").sum()))
col3.metric("Countries Affected", filtered_events["country"].nunique())
col4.metric("Tracked Commodities", filtered_events["commodity"].nunique())

st.divider()

left_col, right_col = st.columns([1.1, 1])

with left_col:
    st.subheader("Live Global Events")
    st.dataframe(filtered_events, use_container_width=True, hide_index=True)

with right_col:
    st.subheader("Live Risk Map")
    render_event_map(filtered_events)

st.divider()
st.subheader("Uploaded BOM Preview")

if uploaded_file is not None:
    try:
        raw_bom_df = load_bom(uploaded_file)
        is_valid, missing_columns = validate_bom(raw_bom_df)

        if not is_valid:
            st.error("Missing required BOM columns: " + ", ".join(missing_columns))
            st.markdown("### Required Minimum Columns")
            st.code("part_name, supplier_country")
        else:
            bom_df = clean_bom(raw_bom_df)
            st.success("BOM uploaded and validated successfully.")
            st.dataframe(bom_df, use_container_width=True, hide_index=True)

            risk_df = analyze_bom_risk(bom_df, filtered_events)

            st.subheader("Affected BOM Items")

            if not risk_df.empty:
                risk_df = add_recommendations(risk_df, bom_df)
                filtered_risk_df = risk_df[risk_df["risk_level"].isin(selected_risk_levels)].copy()

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

                st.dataframe(
                    filtered_risk_df[display_cols],
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
    st.warning("Upload a BOM file from the sidebar to begin analysis.")

    sample_bom = get_bom_template()
    st.markdown("### Sample BOM Format")
    st.dataframe(sample_bom, use_container_width=True, hide_index=True)

    csv_data = sample_bom.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Sample BOM Template",
        data=csv_data,
        file_name="sample_bom_template.csv",
        mime="text/csv"
    )
