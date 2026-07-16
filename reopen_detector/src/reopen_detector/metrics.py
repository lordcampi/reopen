"""Metrics calculation for the Streamlit UI."""

import pandas as pd


def calculate_metrics(filtered_reopens: pd.DataFrame) -> dict:
    """Calculate summary metrics for the selected date range.

    Args:
        filtered_reopens: Reopen rows within the selected date range.

    Returns:
        Dictionary with metric names and values.
    """
    reopens_in_range = len(filtered_reopens)
    cases_with_reopen = (
        filtered_reopens["case_number"].nunique()
        if not filtered_reopens.empty
        else 0
    )

    return {
        "Cantidad de Reopen": reopens_in_range,
        "Casos con reopen": cases_with_reopen,
    }
