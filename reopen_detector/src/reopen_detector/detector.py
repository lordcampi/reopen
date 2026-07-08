"""Core reopen detection logic."""

import pandas as pd

from reopen_detector.config import RESOLVED_VALUE


def detect_reopens(df: pd.DataFrame) -> pd.DataFrame:
    """Detect reopen cases from normalized interaction data.

    For each case_number:
    1. Find the first event where NewValue == 'resolved'.
    2. Find the first interaction after that resolved event.
    3. If no subsequent interaction exists, skip (not a reopen).
    4. If subsequent interaction exists, classify:
       - reopen_confirmado: post-resolved NewValue != 'resolved'
       - reopen_por_resolved_multiple: post-resolved NewValue == 'resolved'

    Args:
        df: Normalized DataFrame with columns:
            case_number, StartTime, NewValue, Email.
            Must be sorted by case_number and StartTime.

    Returns:
        DataFrame with columns:
            case_number, resolved_date, reopen_date, agent,
            detection_type, post_resolved_new_value
    """
    results = []

    for case_number, group in df.groupby("case_number"):
        # Group is already sorted by StartTime (from normalizer)
        group = group.reset_index(drop=True)

        # Find rows where NewValue is 'resolved'
        resolved_mask = group["NewValue"] == RESOLVED_VALUE
        resolved_indices = group.index[resolved_mask].tolist()

        if not resolved_indices:
            # No resolved event -> no reopen
            continue

        first_resolved_idx = resolved_indices[0]
        resolved_date = group.loc[first_resolved_idx, "StartTime"]

        # Check if there's any interaction after the first resolved
        if first_resolved_idx >= len(group) - 1:
            # Resolved is the last event -> no reopen
            continue

        # Get the first subsequent interaction
        subsequent_idx = first_resolved_idx + 1
        subsequent_row = group.loc[subsequent_idx]

        reopen_date = subsequent_row["StartTime"]
        agent = subsequent_row["Email"]
        post_resolved_new_value = subsequent_row["NewValue"]

        # Classify
        if post_resolved_new_value == RESOLVED_VALUE:
            detection_type = "reopen_por_resolved_multiple"
        else:
            detection_type = "reopen_confirmado"

        results.append(
            {
                "case_number": case_number,
                "resolved_date": resolved_date,
                "reopen_date": reopen_date,
                "agent": agent,
                "detection_type": detection_type,
                "post_resolved_new_value": post_resolved_new_value,
            }
        )

    if not results:
        return pd.DataFrame(
            columns=[
                "case_number",
                "resolved_date",
                "reopen_date",
                "agent",
                "detection_type",
                "post_resolved_new_value",
            ]
        )

    return pd.DataFrame(results)