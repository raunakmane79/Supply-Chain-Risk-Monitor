import pandas as pd


def generate_recommendation(row: pd.Series) -> str:
    risk_level = str(row.get("risk_level", "Low")).strip().title()
    event_type = str(row.get("event_type", "")).strip().lower()
    commodity = str(row.get("commodity", "")).strip()
    supplier_country = str(row.get("supplier_country", "")).strip()
    alternate_supplier = str(row.get("alternate_supplier", "")).strip()
    criticality = str(row.get("criticality", "Medium")).strip().title()

    actions = []

    if risk_level == "High":
        actions.append("Contact supplier immediately for disruption status and recovery ETA")
        actions.append("Review open purchase orders and expedite critical shipments")
    elif risk_level == "Medium":
        actions.append("Monitor supplier closely and confirm short-term supply continuity")
        actions.append("Review current inventory coverage for this part")
    else:
        actions.append("Continue monitoring; no immediate escalation required")

    if not alternate_supplier:
        actions.append("Identify and qualify a backup supplier")
    else:
        actions.append(f"Evaluate alternate supplier option: {alternate_supplier}")

    if event_type in {"earthquake", "flood", "storm", "wildfire"}:
        actions.append("Increase short-term safety stock to buffer disruption risk")

    if event_type in {"conflict", "protest"}:
        actions.append("Assess logistics rerouting and region diversification options")

    if commodity:
        actions.append(f"Review market exposure for {commodity} and prepare for cost volatility")

    if criticality == "High":
        actions.append("Escalate to sourcing and operations leadership due to high part criticality")

    # Remove duplicates while preserving order
    seen = set()
    unique_actions = []
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique_actions.append(action)

    return " | ".join(unique_actions)


def add_recommendations(risk_df: pd.DataFrame, bom_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge BOM fields needed for recommendations and generate recommendation text.
    """
    if risk_df.empty:
        return risk_df

    merge_columns = [
        "part_number",
        "alternate_supplier",
        "criticality",
    ]

    bom_merge = bom_df[merge_columns].copy() if all(
        col in bom_df.columns for col in merge_columns
    ) else bom_df.copy()

    enriched_df = risk_df.merge(
        bom_merge,
        on="part_number",
        how="left",
        suffixes=("", "_bom")
    )

    if "criticality_bom" in enriched_df.columns:
        enriched_df["criticality"] = enriched_df["criticality_bom"].fillna(enriched_df.get("criticality", "Medium"))

    if "alternate_supplier_bom" in enriched_df.columns:
        enriched_df["alternate_supplier"] = enriched_df["alternate_supplier_bom"].fillna(
            enriched_df.get("alternate_supplier", "")
        )

    enriched_df["recommendation"] = enriched_df.apply(generate_recommendation, axis=1)
    return enriched_df
