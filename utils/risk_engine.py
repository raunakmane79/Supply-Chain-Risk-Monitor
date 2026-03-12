 import pandas as pd


HIGH_SEVERITY_EVENTS = {"High": 20, "Medium": 10, "Low": 5}

CRITICALITY_SCORES = {"High": 20, "Medium": 10, "Low": 5}


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def calculate_risk_score(
    bom_row: pd.Series,
    event_row: pd.Series,
) -> tuple[int, list[str]]:
    """
    Calculates risk score for one BOM item against one event.
    Returns (score, reasons)
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

    # Geography match
    if supplier_country and event_country and supplier_country == event_country:
        score += 50
        reasons.append(f"Supplier country matches event country ({event_row['country']})")

    # Commodity match
    if commodity and event_commodity and commodity == event_commodity:
        score += 30
        reasons.append(f"Commodity match with impacted commodity ({event_row['commodity']})")
    elif material and event_commodity and material == event_commodity:
        score += 20
        reasons.append(f"Material match with impacted commodity ({event_row['commodity']})")

    # Severity
    score += HIGH_SEVERITY_EVENTS.get(event_severity, 5)
    reasons.append(f"Event severity is {event_severity}")

    # Criticality
    score += CRITICALITY_SCORES.get(criticality, 10)
    reasons.append(f"Part criticality is {criticality}")

    # No alternate supplier
    if not alternate_supplier:
        score += 10
        reasons.append("No alternate supplier listed")

    return score, reasons


def get_risk_level(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def analyze_bom_risk(
    bom_df: pd.DataFrame,
    events_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compare each BOM row with each event and keep the highest-risk match.
    """
    if bom_df.empty or events_df.empty:
        return pd.DataFrame()

    results = []

    for _, bom_row in bom_df.iterrows():
        best_match = None
        best_score = -1
        best_reasons = []

        for _, event_row in events_df.iterrows():
            score, reasons = calculate_risk_score(bom_row, event_row)

            if score > best_score:
                best_score = score
                best_match = event_row
                best_reasons = reasons

        risk_level = get_risk_level(best_score)

        results.append(
            {
                "part_number": bom_row.get("part_number", ""),
                "part_name": bom_row.get("part_name", ""),
                "commodity": bom_row.get("commodity", ""),
                "supplier_name": bom_row.get("supplier_name", ""),
                "supplier_country": bom_row.get("supplier_country", ""),
                "criticality": bom_row.get("criticality", ""),
                "matched_event": best_match.get("title", "") if best_match is not None else "",
                "event_type": best_match.get("event_type", "") if best_match is not None else "",
                "event_country": best_match.get("country", "") if best_match is not None else "",
                "impacted_commodity": best_match.get("commodity", "") if best_match is not None else "",
                "event_severity": best_match.get("severity", "") if best_match is not None else "",
                "risk_score": best_score,
                "risk_level": risk_level,
                "reason": " | ".join(best_reasons),
            }
        )

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="risk_score", ascending=False).reset_index(drop=True)
    return results_df
