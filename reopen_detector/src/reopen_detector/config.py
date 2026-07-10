"""Project constants and configuration."""

REQUIRED_COLUMNS = ["StartTime", "NewValue", "Email", "case_number"]
RESOLVED_VALUE = "resolved"

# NULL-like values to normalize to empty string
NULL_VALUES = {"null", "none", "nan", "", " "}

# Column names for visible output
VISIBLE_COLUMNS_MAP = {
    "case_number": "Número de caso",
    "reopen_date": "Fecha",
    "agent": "Agente",
}

# Column names for aggregated visible output (one row per case)
AGGREGATED_COLUMNS_MAP = {
    "case_number": "Número de caso",
    "reopen_count": "Reaperturas en el período",
    "last_reopen_date": "Última fecha de reapertura",
    "last_agent": "Último agente",
}

# Technical detail columns
TECHNICAL_COLUMNS = [
    "case_number",
    "resolved_date",
    "reopen_date",
    "agent",
    "detection_type",
    "post_resolved_new_value",
]

# Spanish month mapping for date parsing
SPANISH_MONTHS = {
    "ene": "jan",
    "feb": "feb",
    "mar": "mar",
    "abr": "apr",
    "may": "may",
    "jun": "jun",
    "jul": "jul",
    "ago": "aug",
    "sep": "sep",
    "sept": "sep",
    "oct": "oct",
    "nov": "nov",
    "dic": "dec",
}

# CSV separators to try (in order)
CSV_SEPARATORS = [",", ";", "\t"]

# Encodings to try (in order)
CSV_ENCODINGS = ["utf-8", "latin-1"]