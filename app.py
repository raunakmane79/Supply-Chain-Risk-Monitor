import streamlit as st
import pandas as pd

from utils.bom_parser import load_bom, validate_bom, clean_bom, get_bom_template


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
            "severity": "High"
        },
        {
            "event_type": "Flood",
            "title": "Flooding impacting port operations in China",
            "country": "China",
            "commodity": "Electronics",
            "severity": "Medium"
        },
        {
            "event_type": "Conflict",
            "title": "Conflict risk affecting metal shipments",
            "country": "Ukraine",
            "commodity": "Steel",
            "severity": "High"
        },
        {
            "event_type": "Storm",
            "title": "Storm disruption near Chile logistics corridor",
            "country": "Chile",
            "commodity": "Copper",
            "severity": "Medium"
        }
    ]
    return pd.DataFrame(data)


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

# Load sample live events for now
events_df = load_sample_events()

# Apply filters
filtered_events = events_df[
    events_df["event_type"].isin(selected_event_types) &
    events_df["severity"].isin(selected_severity)
].copy()

# Top metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Live Events", len(filtered_events))
col2.metric("High Severity Events", int((filtered_events["severity"] == "High").sum()))
col3.metric("Countries Affected", filtered_events["country"].nunique())
col4.metric("Tracked Commodities", filtered_events["commodity"].nunique())

st.divider()

# Main layout
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("Live Global Events")
    st.dataframe(filtered_events, use_container_width=True, hide_index=True)

with right_col:
    st.subheader("Live Risk Map Placeholder")
    st.info("Map will be added in the next step using PyDeck.")

st.divider()

st.subheader("Uploaded BOM Preview")

if uploaded_file is not None:
    try:
        raw_bom_df = load_bom(uploaded_file)
        is_valid, missing_columns = validate_bom(raw_bom_df)

        if not is_valid:
            st.error(
                "Missing required BOM columns: "
                + ", ".join(missing_columns)
            )
            st.markdown("### Required Minimum Columns")
            st.code("part_name, supplier_country")
        else:
            bom_df = clean_bom(raw_bom_df)
            st.success("BOM uploaded and validated successfully.")
            st.dataframe(bom_df, use_container_width=True, hide_index=True)

            st.subheader("Affected BOM Items Placeholder")
            st.info("Risk matching engine will be added in the next step.")

            st.subheader("Recommendations Placeholder")
            st.info("Procurement recommendations will appear here after risk analysis is built.")

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
