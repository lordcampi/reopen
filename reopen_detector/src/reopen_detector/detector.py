"""Core reopen detection logic."""

from datetime import date, datetime, time

import pandas as pd

from reopen_detector.config import RESOLVED_VALUE


def detect_reopens(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> pd.DataFrame:
    """Detect reopen cases from normalized interaction data.

    For each case_number:
    1. Find the first event where NewValue == 'resolved'.
    2. Find the first interaction after that resolved event.
    3. If no subsequent interaction exists, skip (not a reopen).
    4. If subsequent interaction exists, classify:
       - reopen_confirmado: post-resolved NewValue != 'resolved'
       - reopen_por_resolved_multiple: post-resolved NewValue == 'resolved'

    Additionally, if start_date and/or end_date are provided, a third
    strategy is applied:

    5. reopen_por_resolved_en_rango: the case has at least one resolved
       anywhere in its history AND at least one resolved within the
       specified date range (and both are different resolved events,
       i.e. total resolved count >= 2).

    Args:
        df: Normalized DataFrame with columns:
            case_number, StartTime, NewValue, Email.
            Must be sorted by case_number and StartTime.
        start_date: Optional start of the query date range (inclusive).
        end_date: Optional end of the query date range (inclusive).
        start_time: Optional start time of day (UY local, defaults to 00:00:00).
        end_time: Optional end time of day (UY local, defaults to 23:59:59).

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

    # -------------------------------------------------------------------
    # Strategy 3: reopen_por_resolved_en_rango
    # A case has >= 2 resolved events total, and at least one of them
    # falls within the query date range.
    # -------------------------------------------------------------------
    if start_date is not None or end_date is not None:
        # Build full datetime range bounds (date + time)
        st = start_time if start_time is not None else time(0, 0)
        et = end_time if end_time is not None else time(23, 59, 59)

        range_start = datetime.combine(start_date, st) if start_date is not None else None
        range_end = datetime.combine(end_date, et) if end_date is not None else None

        for case_number, group in df.groupby("case_number"):
            group = group.reset_index(drop=True)

            resolved_mask = group["NewValue"] == RESOLVED_VALUE
            resolved_rows = group[resolved_mask]

            total_resolved = len(resolved_rows)
            if total_resolved < 2:
                continue

            # Check if at least one resolved falls within the full
            # datetime range (date + time, UY local).
            has_resolved_in_range = False
            first_in_range_date = None
            for _, resolved_row in resolved_rows.iterrows():
                resolved_dt = resolved_row["StartTime"]

                # Convert to Python datetime for consistent comparison
                if isinstance(resolved_dt, pd.Timestamp):
                    resolved_dt = resolved_dt.to_pydatetime()

                if not isinstance(resolved_dt, datetime):
                    continue

                in_range = True
                if range_start is not None and resolved_dt < range_start:
                    in_range = False
                if range_end is not None and resolved_dt > range_end:
                    in_range = False

                if in_range:
                    has_resolved_in_range = True
                    if first_in_range_date is None:
                        first_in_range_date = resolved_dt
                        first_in_range_agent = resolved_row["Email"]
                    # Don't break — we still want the very first in-range
                    # for the record, so we only set first_in_range_date once

            if has_resolved_in_range:
                # Use the first resolved within range as the reopen_date
                # The resolved_date is the first resolved in the entire history
                first_resolved_all = resolved_rows.iloc[0]
                results.append(
                    {
                        "case_number": case_number,
                        "resolved_date": first_resolved_all["StartTime"],
                        "reopen_date": first_in_range_date,
                        "agent": first_in_range_agent,
                        "detection_type": "reopen_por_resolved_en_rango",
                        "post_resolved_new_value": RESOLVED_VALUE,
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
