import pandas as pd


SEVERITY_SCORES = {"High": 20, "Medium": 10, "Low": 5}
CRITICALITY_SCORES = {"High": 20, "Medium": 10, "Low": 5}


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def calculate_risk_score(
    bom_row: pd.Series,
    event_row: pd.Series,
) -> tuple[int, list[str], bool]:
    """
    Calculates risk score for one BOM item against one event.
    Returns:
        score, reasons, is_relevant_match
    """
    score = 0
    reasons = []

    supplier_country = normalize_text(bom_row.get("supplier_country", ""))
    commodity = normalize_text(bom_row.get("commodity", ""))
    material = normalize_text(bom_row.get("material", ""))
    criticality = str(bom_row.get("criticality", "Medium")).strip().title()
    alternate_supplier = normalize_text(bom_row.get("alternate_supplier", ""))

    event_country = normalize_text(event_row.get("country", ""))
    event_commodity = normalize_text(event_row.get("commodity", ""))
    event_severity = str(event_row.get("severity", "Low")).strip().title()

    geography_match = False
    commodity_match = False

    # Geography match
    if supplier_country and event_country and supplier_country == event_country:
        score += 50
        geography_match = True
        reasons.append(f"Supplier country matches event country ({event_row['country']})")

    # Commodity / material match
    if commodity and event_commodity and commodity == event_commodity:
        score += 30
        commodity_match = True
        reasons.append(f"Commodity match with impacted commodity ({event_row['commodity']})")
    elif material and event_commodity and material == event_commodity:
        score += 20
        commodity_match = True
        reasons.append(f"Material match with impacted commodity ({event_row['commodity']})")

    # Only meaningful if at least geography or commodity match exists
    is_relevant_match = geography_match or commodity_match

    if is_relevant_match:
        score += SEVERITY_SCORES.get(event_severity, 5)
        reasons.append(f"Event severity is {event_severity}")

        score += CRITICALITY_SCORES.get(criticality, 10)
        reasons.append(f"Part criticality is {criticality}")

        if not alternate_supplier:
            score += 10
            reasons.append("No alternate supplier listed")

    return score, reasons, is_relevant_match


def get_risk_level(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    if score > 0:
        return "Low"
    return "No Direct Risk"


def analyze_bom_risk(
    bom_df: pd.DataFrame,
    events_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compare each BOM row with each event and keep the highest-risk relevant match.
    """
    if bom_df.empty or events_df.empty:
        return pd.DataFrame()

    results = []

    for _, bom_row in bom_df.iterrows():
        best_match = None
        best_score = 0
        best_reasons = []
        found_relevant_match = False

        for _, event_row in events_df.iterrows():
            score, reasons, is_relevant_match = calculate_risk_score(bom_row, event_row)

            if is_relevant_match and score > best_score:
                best_score = score
                best_match = event_row
                best_reasons = reasons
                found_relevant_match = True

        if found_relevant_match and best_match is not None:
            risk_level = get_risk_level(best_score)

            results.append(
                {
                    "part_number": bom_row.get("part_number", ""),
                    "part_name": bom_row.get("part_name", ""),
                    "commodity": bom_row.get("commodity", ""),
                    "supplier_name": bom_row.get("supplier_name", ""),
                    "supplier_country": bom_row.get("supplier_country", ""),
                    "criticality": bom_row.get("criticality", ""),
                    "alternate_supplier": bom_row.get("alternate_supplier", ""),
                    "matched_event": best_match.get("title", ""),
                    "event_type": best_match.get("event_type", ""),
                    "event_country": best_match.get("country", ""),
                    "impacted_commodity": best_match.get("commodity", ""),
                    "event_severity": best_match.get("severity", ""),
                    "risk_score": best_score,
                    "risk_level": risk_level,
                    "reason": " | ".join(best_reasons),
                }
            )

    if not results:
        return pd.DataFrame()

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="risk_score", ascending=False).reset_index(drop=True)
    return results_df
