import json
import streamlit as st
from google import genai

client = genai.Client(api_key=st.secrets["AIzaSyDNMk0aDVMPfy0_321V9FpUeasLY9thgQw"])


def _extract_text(response) -> str:
    try:
        return response.text
    except Exception:
        pass

    # Fallback
    try:
        candidates = getattr(response, "candidates", [])
        if candidates:
            parts = candidates[0].content.parts
            return "".join(getattr(p, "text", "") for p in parts if hasattr(p, "text"))
    except Exception:
        pass

    return ""


def _load_json(response) -> dict:
    text = _extract_text(response).strip()

    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    return json.loads(text)


def generate_ai_risk_commentary(events_summary: dict, bom_summary: dict) -> dict:
    prompt = f"""
You are a senior supply chain risk analyst.

Analyze the live disruption summary and BOM risk summary.

Return ONLY valid JSON in this exact shape:
{{
  "executive_summary": "string",
  "top_risks": ["string", "string", "string"],
  "recommended_action": "string",
  "urgency": "Low|Medium|High"
}}

Live events summary:
{json.dumps(events_summary, indent=2)}

BOM summary:
{json.dumps(bom_summary, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
    )

    return _load_json(response)


def rank_alternate_sources(part_context: dict) -> dict:
    prompt = f"""
You are an industrial supply chain analyst.

Rank alternate sourcing options for the impacted part.
Prioritize resilience, geopolitical risk reduction, commodity exposure,
practicality, and continuity of supply.

Return ONLY valid JSON in this exact shape:
{{
  "best_option": "string",
  "ranking": [
    {{
      "supplier": "string",
      "rank": 1,
      "score": 0,
      "reason": "string"
    }}
  ],
  "switch_recommendation": "string"
}}

Part context:
{json.dumps(part_context, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
    )

    return _load_json(response)


def generate_scenario_commentary(scenario_context: dict) -> dict:
    prompt = f"""
You are a supply chain scenario planning analyst.

Assess this disruption scenario.

Return ONLY valid JSON in this exact shape:
{{
  "scenario_summary": "string",
  "operational_impact": "string",
  "procurement_impact": "string",
  "recommended_response": "string"
}}

Scenario context:
{json.dumps(scenario_context, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
    )

    return _load_json(response)
