import json
import streamlit as st

try:
    from google import genai
except ImportError as e:
    raise ImportError(
        "Gemini SDK not installed. Add 'google-genai' to requirements.txt and redeploy."
    ) from e


client = genai.Client(api_key=st.secrets["AIzaSyDNMk0aDVMPfy0_321V9FpUeasLY9thgQw"])


def _extract_text(response) -> str:
    try:
        return response.text
    except Exception:
        return ""


def _load_json(response) -> dict:
    text = _extract_text(response).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return json.loads(text)


def generate_ai_risk_commentary(events_summary: dict, bom_summary: dict) -> dict:
    prompt = f"""
You are a senior supply chain risk analyst.
Return ONLY valid JSON:
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
Return ONLY valid JSON:
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
Return ONLY valid JSON:
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
