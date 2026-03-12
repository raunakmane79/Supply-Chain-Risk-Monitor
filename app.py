import streamlit as st
import pandas as pd

from utils.bom_parser import load_bom, validate_bom, clean_bom, get_bom_template
from utils.risk_engine import analyze_bom_risk


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

            risk_df = analyze_bom_risk(bom_df, filtered_events)

            st.subheader("Affected BOM Items")

            if not risk_df.empty:
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
                    risk_df[display_cols],
                    use_container_width=True,
                    hide_index=True
                )

                high_risk_count = int((risk_df["risk_level"] == "High").sum())
                medium_risk_count = int((risk_df["risk_level"] == "Medium").sum())
                low_risk_count = int((risk_df["risk_level"] == "Low").sum())

                c1, c2, c3 = st.columns(3)
                c1.metric("High Risk Parts", high_risk_count)
                c2.metric("Medium Risk Parts", medium_risk_count)
                c3.metric("Low Risk Parts", low_risk_count)

                st.subheader("Detailed Risk Explanation")
                st.dataframe(
                    risk_df[[
                        "part_name",
                        "supplier_name",
                        "supplier_country",
                        "matched_event",
                        "risk_level",
                        "reason"
                    ]],
                    use_container_width=True,
                    hide_index=True
                )

            else:
                st.info("No risk results generated.")

            st.subheader("Recommendations Placeholder")
            st.info("Procurement recommendations will appear here after the recommendation engine is built.")

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
