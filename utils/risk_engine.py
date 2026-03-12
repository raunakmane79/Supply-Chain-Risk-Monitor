import pandas as pd


def _normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def infer_conflict_commodities(event_title: str, event_country: str, event_type: str):
    text = f"{event_title} {event_country} {event_type}".lower()

    if any(x in text for x in ["iran", "hormuz", "middle east", "oil", "lng", "gas", "petroleum", "crude"]):
        return ["crude oil", "natural gas", "lng", "petrochemicals", "oil"]

    if any(x in text for x in ["taiwan", "chip", "semiconductor", "electronics", "microchip"]):
        return ["semiconductor", "microchips", "memory chips", "electronics"]

    if any(x in text for x in ["chile", "peru", "copper", "mining strike"]):
        return ["copper"]

    if any(x in text for x in ["lithium", "nickel", "cobalt", "battery", "graphite"]):
        return ["lithium", "nickel", "cobalt", "batteries", "graphite"]

    if any(x in text for x in ["shipping", "port", "freight", "container", "red sea", "blockade", "vessel"]):
        return ["logistics", "imported parts", "electronics", "semiconductor"]

    if any(x in text for x in ["rare earth", "export restriction", "china export"]):
        return ["rare earth elements", "metals", "electronics"]

    return []


def calculate_risk_level(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def analyze_bom_risk(bom_df: pd.DataFrame, events_df: pd.DataFrame, home_country: str = "United States") -> pd.DataFrame:
    if bom_df.empty or events_df.empty:
        return pd.DataFrame()

    results = []

    for _, bom_row in bom_df.iterrows():
        part_name = bom_row.get("part_name", "")
        part_number = bom_row.get("part_number", "")
        commodity = _normalize_text(bom_row.get("commodity", ""))
        supplier_country = _normalize_text(bom_row.get("supplier_country", ""))
        supplier_name = bom_row.get("supplier_name", "")
        criticality = _normalize_text(bom_row.get("criticality", ""))

        best_match = None
        best_score = 0
        best_reason = ""
        best_rule_trigger = ""
        best_inferred_commodities = ""

        for _, event_row in events_df.iterrows():
            event_title = str(event_row.get("title", ""))
            event_country = _normalize_text(event_row.get("country", ""))
            event_type = str(event_row.get("event_type", ""))
            event_severity = str(event_row.get("severity", ""))
            event_commodity = _normalize_text(event_row.get("commodity", ""))

            score = 0
            reasons = []
            triggers = []

            inferred_commodities = infer_conflict_commodities(event_title, event_country, event_type)
            inferred_commodities_norm = [_normalize_text(x) for x in inferred_commodities]

            if supplier_country and event_country and supplier_country == event_country:
                score += 35
                reasons.append("Supplier country is directly affected by this live event.")
                triggers.append("supplier_country_match")

            if commodity and event_commodity and commodity == event_commodity:
                score += 30
                reasons.append("BOM commodity directly matches the event commodity.")
                triggers.append("commodity_match")

            if commodity and commodity in inferred_commodities_norm:
                score += 35
                reasons.append("Event title implies disruption to this BOM commodity.")
                triggers.append("commodity_inference_match")

            if event_type in ["Conflict", "Sanctions", "Shipping Disruption"]:
                score += 10
                reasons.append("Geopolitical event type increases supply risk.")
                triggers.append("geopolitical_event_type")

            if event_severity == "High":
                score += 20
                reasons.append("Event severity is high.")
                triggers.append("high_event_severity")
            elif event_severity == "Medium":
                score += 10
                reasons.append("Event severity is medium.")
                triggers.append("medium_event_severity")

            if criticality == "high":
                score += 15
                reasons.append("Part is marked as high criticality.")
                triggers.append("high_part_criticality")
            elif criticality == "medium":
                score += 8
                reasons.append("Part is marked as medium criticality.")
                triggers.append("medium_part_criticality")

            if score > best_score:
                best_score = score
                best_match = event_row
                best_reason = " ".join(reasons)
                best_rule_trigger = ", ".join(triggers)
                best_inferred_commodities = ", ".join(inferred_commodities)

        if best_match is not None and best_score > 0:
            results.append(
                {
                    "part_number": part_number,
                    "part_name": part_name,
                    "commodity": bom_row.get("commodity", ""),
                    "supplier_name": supplier_name,
                    "supplier_country": bom_row.get("supplier_country", ""),
                    "matched_event": best_match.get("title", ""),
                    "event_type": best_match.get("event_type", ""),
                    "impacted_commodity": best_match.get("commodity", ""),
                    "inferred_commodities": best_inferred_commodities,
                    "risk_score": best_score,
                    "risk_level": calculate_risk_level(best_score),
                    "rule_trigger": best_rule_trigger,
                    "reason": best_reason,
                }
            )

    return pd.DataFrame(results)
