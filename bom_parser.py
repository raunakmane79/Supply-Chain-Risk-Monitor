import pandas as pd

REQUIRED_COLUMNS = ["part_name", "supplier_country"]
OPTIONAL_COLUMNS = [
    "part_number",
    "commodity",
    "material",
    "supplier_name",
    "supplier_city",
    "annual_usage",
    "unit_cost",
    "criticality",
    "alternate_supplier",
]


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]
    return df


def load_bom(uploaded_file) -> pd.DataFrame:
    """
    Load CSV or Excel BOM file into a DataFrame.
    """
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

    if df.empty:
        raise ValueError("The uploaded BOM file is empty.")

    df = standardize_columns(df)
    return df


def validate_bom(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Validate required BOM columns.
    """
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        return False, missing_columns

    return True, []


def clean_bom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean BOM data and ensure expected fields exist.
    """
    df = df.copy()

    # Add optional columns if missing
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Fill required text fields safely
    text_columns = [
        "part_number",
        "part_name",
        "commodity",
        "material",
        "supplier_name",
        "supplier_country",
        "supplier_city",
        "criticality",
        "alternate_supplier",
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # Numeric cleanup
    numeric_columns = ["annual_usage", "unit_cost"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Default values
    if "criticality" in df.columns:
        df["criticality"] = df["criticality"].replace("", "Medium")

    return df


def get_bom_template() -> pd.DataFrame:
    """
    Returns a sample BOM template DataFrame.
    """
    return pd.DataFrame(
        [
            {
                "part_number": "P1001",
                "part_name": "PCB Assembly",
                "commodity": "Semiconductor",
                "material": "Electronics",
                "supplier_name": "ABC Circuits",
                "supplier_country": "Taiwan",
                "supplier_city": "Taichung",
                "annual_usage": 5000,
                "unit_cost": 32,
                "criticality": "High",
                "alternate_supplier": "XYZ Electronics",
            },
            {
                "part_number": "P1002",
                "part_name": "Copper Wiring",
                "commodity": "Copper",
                "material": "Metal",
                "supplier_name": "Metro Metals",
                "supplier_country": "Chile",
                "supplier_city": "Santiago",
                "annual_usage": 9000,
                "unit_cost": 6,
                "criticality": "Medium",
                "alternate_supplier": "Alt Copper Ltd",
            },
            {
                "part_number": "P1003",
                "part_name": "Steel Bracket",
                "commodity": "Steel",
                "material": "Metal",
                "supplier_name": "ForgePro",
                "supplier_country": "India",
                "supplier_city": "Pune",
                "annual_usage": 12000,
                "unit_cost": 3,
                "criticality": "Low",
                "alternate_supplier": "SteelWorks",
            },
            {
                "part_number": "P1004",
                "part_name": "Lithium Cell",
                "commodity": "Lithium",
                "material": "Battery Material",
                "supplier_name": "VoltSource",
                "supplier_country": "China",
                "supplier_city": "Shenzhen",
                "annual_usage": 7000,
                "unit_cost": 18,
                "criticality": "High",
                "alternate_supplier": "PowerCell",
            },
        ]
    )
