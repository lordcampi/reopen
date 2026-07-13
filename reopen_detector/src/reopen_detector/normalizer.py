"""Data cleaning and normalization."""

import re
from datetime import datetime

import pandas as pd

from reopen_detector.config import NULL_VALUES, SPANISH_MONTHS


def normalize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Clean and prepare the DataFrame for analysis.

    Returns:
        Tuple of (normalized DataFrame, count of rows with invalid StartTime).
    """
    df = df.copy()

    # Strip whitespace from string columns
    string_columns = ["NewValue", "Email", "case_number", "Country"]
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Normalize case_number as text
    if "case_number" in df.columns:
        df["case_number"] = df["case_number"].astype(str).str.strip()

    # Normalize Email
    if "Email" in df.columns:
        df["Email"] = df["Email"].astype(str).str.strip().str.lower()

    # Normalize NewValue to lowercase
    if "NewValue" in df.columns:
        df["NewValue"] = df["NewValue"].astype(str).str.strip().str.lower()

    # Convert null-like values to empty string in NewValue
    if "NewValue" in df.columns:
        df["NewValue"] = df["NewValue"].apply(
            lambda x: "" if x in NULL_VALUES else x
        )

    # Parse StartTime to datetime
    if "StartTime" in df.columns:
        df["StartTime"], invalid_start = _parse_dates(df, "StartTime")
    else:
        invalid_start = 0

    # Parse SuccessfulTime to datetime if it exists
    if "SuccessfulTime" in df.columns:
        df["SuccessfulTime"], _ = _parse_dates(df, "SuccessfulTime")

    # Mark rows with invalid StartTime (keep them but mark)
    # We drop rows where StartTime couldn't be parsed
    df = df.dropna(subset=["StartTime"])

    # Sort by case_number and StartTime
    df = df.sort_values(by=["case_number", "StartTime"]).reset_index(drop=True)

    return df, invalid_start


def _parse_dates(df: pd.DataFrame, column: str) -> tuple[pd.Series, int]:
    """Parse datetime column with support for Spanish month names.

    Returns:
        Tuple of (parsed datetime Series, count of invalid/missing values).
    """
    dates = pd.Series([pd.NaT] * len(df), index=df.index)
    invalid_count = 0

    for idx, val in df[column].items():
        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() in NULL_VALUES:
            invalid_count += 1
            continue

        parsed = _try_parse_datetime(str(val).strip())
        if parsed is not None:
            dates.at[idx] = parsed
        else:
            invalid_count += 1

    return dates, invalid_count


def _try_parse_datetime(value: str) -> datetime | None:
    """Try to parse a datetime string with multiple format strategies.

    Args:
        value: String representation of a datetime.

    Returns:
        Parsed datetime or None if unparseable.
    """
    # Convert Spanish month names to English
    value_en = _replace_spanish_months(value.lower())

    # Remove comma if present (e.g., "7 jul 2026, 8:13:41")
    value_en = value_en.replace(",", "")

    # List of format strings to try
    formats = [
        # Standard formats
        "%d %b %Y %H:%M:%S",
        "%d %b %y %H:%M:%S",
        "%d %B %Y %H:%M:%S",
        "%d %B %y %H:%M:%S",
        "%b %d %Y %H:%M:%S",
        "%B %d %Y %H:%M:%S",
        # ISO-like formats
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        # Common variants
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        # With AM/PM
        "%d %b %Y %I:%M:%S %p",
        "%d %b %Y %I:%M %p",
        # Date only
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value_en, fmt)
        except ValueError:
            continue

    return None


def _replace_spanish_months(text: str) -> str:
    """Replace Spanish month abbreviations with English ones."""
    result = text
    for spanish, english in SPANISH_MONTHS.items():
        # Use word boundaries to avoid partial replacements
        pattern = r'\b' + re.escape(spanish) + r'\b'
        result = re.sub(pattern, english, result)
    return result