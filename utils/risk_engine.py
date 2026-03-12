import json
from pathlib import Path
import pandas as pd


SEVERITY_SCORES = {"High": 20, "Medium": 10, "Low": 5}
CRITICALITY_SCORES = {"High": 20, "Medium": 10, "Low": 5}

EAST_ASIA_COUNTRIES = {
    "China", "Taiwan", "Japan", "South Korea", "North Korea",
    "Hong Kong", "Mongolia", "Macau"
}

MINING_REGION_COUNTRIES = {
    "Chile", "Peru", "Argentina", "South Africa", "Australia", "Brazil"
}


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def title_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().title()


def load_commodity_rules() -> dict:
    rules_path = Path(__file__).resolve().parent.parent / "data" / "commodity_rules.json"
    if not rules_path.exists():
        return {}
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


COMMODITY_RULES = load_commodity_rules()


def infer_region(country: str) -> str:
    country = title_text(country)
    if country in EAST_ASIA_COUNTRIES:
        return "East Asia"
    if country in {"Ukraine", "Russia", "Poland", "Turkey"}:
        return "Eastern Europe"
    if country in {"Chile", "Peru", "Argentina", "Brazil"}:
        return "Latin America"
    if country in {"Saudi Arabia", "Iran", "Iraq", "Israel", "Egypt", "Uae"}:
        return "Middle East"
    return "Other"


def infer_impacted_commodities(event_type: str, country: str) -> tuple[list[str], str]:
    event_type = title_text(event_type)
    country = title_text(country)

    event_rules = COMMODITY_RULES.get(event_type, {})
    impacted = []
    rule_trigger = ""

    default_commodities = event_rules.get("default_commodities", [])
    country_overrides = event_rules.get("country_overrides", {})
    region_overrides = event_rules.get("region_overrides", {})

    if country in country_overrides:
        impacted.extend(country_overrides[country])
        rule_trigger = f"{event_type} country rule: {country}"

    region = infer_region(country)
    if region in region_overrides:
        impacted.extend(region_overrides[region])
        rule_trigger = f"{event_type} region rule: {region}"

    impacted.extend(default_commodities)

    # Special logic: protest near mining region
    if event_type == "Protest" and country in MINING_REGION_COUNTRIES:
        impacted.extend(["Copper", "Lithium", "Steel", "Mining"])
        rule_trigger = f"Mining-region strike rule: {country}"

    # Special logic: logistics -> imported parts
    if event_type == "Logistics":
        impacted.extend(["Imported Parts"])

    # Deduplicate while preserving order
    seen = set()
    cleaned = []
    for item in impacted:
        item_norm = normalize_text(item)
        if item_norm and item_norm not in seen:
            seen.add(item_norm)
            cleaned.append(item)

    return cleaned, rule_trigger or f"{event_type} default rule"


def is_imported_part(bom_row: pd.Series, home_country: str = "United States") -> bool:
    supplier_country = title_text(bom_row.get("supplier_country", ""))
    if not supplier_country:
        return False
    return supplier_country != title_text(home_country)


def calculate_risk_score(
    bom_row: pd.Series,
    event_row: pd.Series,
    home_country: str = "United States",
) -> tuple[int, list[str], bool, str, list[str]]:
    score = 0
    reasons = []

    supplier_country = title_text(bom_row.get("supplier_country", ""))
    commodity = title_text(bom_row.get("commodity", ""))
    material = title_text(bom_row.get("material", ""))
    criticality = title_text(bom_row.get("criticality", "Medium")) or "Medium"
    alternate_supplier = normalize_text(bom_row.get("alternate_supplier", ""))

    event_type = title_text(event_row.get("event_type", ""))
    event_country = title_text(event_row.get("country", ""))
    event_commodity = title_text(event_row.get("commodity", ""))
    event_severity = title_text(event_row.get("severity", "Low")) or "Low"

    geography_match = False
    direct_commodity_match = False
    rule_commodity_match = False

    # Geography match
    if supplier_country and event_country and supplier_country == event_country:
        score += 50
        geography_match = True
        reasons.append(f"Supplier country matches event country ({event_country})")

    # Direct commodity match
    if commodity and event_commodity and commodity.lower() == event_commodity.lower():
        score += 30
        direct_commodity_match = True
        reasons.append(f"Direct commodity match with event commodity ({event_commodity})")
    elif material and event_commodity and material.lower() == event_commodity.lower():
        score += 15
        direct_commodity_match = True
        reasons.append(f"Material aligns with event commodity ({event_commodity})")

    # Rule-based commodity inference
    inferred_commodities, rule_trigger = infer_impacted_commodities(event_type, event_country)
    inferred_norm = {normalize_text(x) for x in inferred_commodities}

    if commodity and normalize_text(commodity) in inferred_norm:
        score += 25
        rule_commodity_match = True
        reasons.append(f"Commodity matched inferred impacted commodities ({', '.join(inferred_commodities[:4])})")
    elif material and normalize_text(material) in inferred_norm:
        score += 15
        rule_commodity_match = True
        reasons.append(f"Material matched inferred impacted commodities ({', '.join(inferred_commodities[:4])})")

    # Imported parts logic for logistics
    imported_flag = is_imported_part(bom_row, home_country=home_country)
    if event_type == "Logistics" and imported_flag:
        score += 25
        rule_commodity_match = True
        reasons.append("Logistics disruption may affect imported part flow")

    is_relevant_match = geography_match or direct_commodity_match or rule_commodity_match

    if is_relevant_match:
        score += SEVERITY_SCORES.get(event_severity, 5)
        reasons.append(f"Event severity is {event_severity}")

        score += CRITICALITY_SCORES.get(criticality, 10)
        reasons.append(f"Part criticality is {criticality}")

        if not alternate_supplier:
            score += 10
            reasons.append("No alternate supplier listed")

    return score, reasons, is_relevant_match, rule_trigger, inferred_commodities


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
    events_df: pd.DataFrame,
    home_country: str = "United States",
) -> pd.DataFrame:
    if bom_df.empty or events_df.empty:
        return pd.DataFrame()

    results = []

    for _, bom_row in bom_df.iterrows():
        best_match = None
        best_score = 0
        best_reasons = []
        best_rule_trigger = ""
        best_inferred_commodities = []
        found_relevant_match = False

        for _, event_row in events_df.iterrows():
            score, reasons, is_relevant_match, rule_trigger, inferred_commodities = calculate_risk_score(
                bom_row, event_row, home_country=home_country
            )

            if is_relevant_match and score > best_score:
                best_score = score
                best_match = event_row
                best_reasons = reasons
                best_rule_trigger = rule_trigger
                best_inferred_commodities = inferred_commodities
                found_relevant_match = True

        if found_relevant_match and best_match is not None:
            results.append(
                {
                    "part_number": bom_row.get("part_number", ""),
                    "part_name": bom_row.get("part_name", ""),
                    "commodity": bom_row.get("commodity", ""),
                    "material": bom_row.get("material", ""),
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
                    "risk_level": get_risk_level(best_score),
                    "rule_trigger": best_rule_trigger,
                    "inferred_commodities": ", ".join(best_inferred_commodities),
                    "reason": " | ".join(best_reasons),
                }
            )

    if not results:
        return pd.DataFrame()

    results_df = pd.DataFrame(results)
    return results_df.sort_values(by="risk_score", ascending=False).reset_index(drop=True)
