"""Metrics calculation for the Streamlit UI."""

import pandas as pd


def calculate_metrics(
    raw_row_count: int,
    unique_cases: int,
    invalid_dates: int,
    total_reopens: int,
    reopens_in_range: int,
    unique_cases_with_reopens: int = 0,
) -> dict:
    """Calculate summary metrics.

    Args:
        raw_row_count: Number of rows loaded from CSV.
        unique_cases: Number of unique case numbers after normalization.
        invalid_dates: Number of rows dropped due to invalid StartTime.
        total_reopens: Total reopens detected (before filtering).
        reopens_in_range: Reopens within the selected date range.
        unique_cases_with_reopens: Number of unique cases with at least one
            reopen event.

    Returns:
        Dictionary with metric names and values.
    """
    return {
        "Filas cargadas": raw_row_count,
        "Casos únicos": unique_cases,
        "Filas con fecha inválida": invalid_dates,
        "Reopens detectados (total)": total_reopens,
        "Reopens en rango": reopens_in_range,
        "Casos con reopen": unique_cases_with_reopens,
    }
