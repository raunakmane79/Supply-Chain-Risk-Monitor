# Supply Chain Risk Monitor

A Streamlit-based supply chain intelligence app that translates live global disruptions into BOM-level risk.

## Features

- Live global event monitoring
- Interactive world risk map
- BOM upload with validation
- Part-level risk scoring
- Procurement recommendations
- CSV export of risk analysis

## How it works

1. Pull live disruption events
2. Map events to countries and commodities
3. Upload BOM data
4. Match BOM items to risk events using supplier geography and commodity exposure
5. Generate recommendations for sourcing and operations teams

## BOM Template Fields

Recommended columns:

- part_number
- part_name
- commodity
- material
- supplier_name
- supplier_country
- supplier_city
- annual_usage
- unit_cost
- criticality
- alternate_supplier

Minimum required columns:

- part_name
- supplier_country

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
