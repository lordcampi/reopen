"""V2 reopen detection — one row per Resolved event within the query range."""

from datetime import date, datetime, time

import pandas as pd

from reopen_detector.config import RESOLVED_VALUE


def detect_reopens_v2(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> pd.DataFrame:
    """Detect reopen cycles for V2 range analysis.

    For each case, every ``Resolved`` event whose ``StartTime`` falls within
    the query datetime range produces one row.  The first ``Resolved`` in the
    case history is skipped because it closes the initial cycle, not a reopen.

    Args:
        df: Normalized DataFrame sorted by case_number and StartTime.
        start_date: Optional inclusive start date (UY local).
        end_date: Optional inclusive end date (UY local).
        start_time: Optional start time of day (defaults to 00:00:00).
        end_time: Optional end time of day (defaults to 23:59:59).

    Returns:
        DataFrame with the same columns as ``detect_reopens``.
    """
    empty = pd.DataFrame(
        columns=[
            "case_number",
            "resolved_date",
            "reopen_date",
            "agent",
            "detection_type",
            "post_resolved_new_value",
            "country",
        ]
    )

    if start_date is None and end_date is None:
        return empty

    st = start_time if start_time is not None else time(0, 0)
    et = end_time if end_time is not None else time(23, 59, 59)
    range_start = datetime.combine(start_date, st) if start_date is not None else None
    range_end = datetime.combine(end_date, et) if end_date is not None else None

    has_country = "Country" in df.columns
    results = []

    for case_number, group in df.groupby("case_number"):
        group = group.reset_index(drop=True)
        resolved_rows = group[group["NewValue"] == RESOLVED_VALUE].reset_index(drop=True)

        if len(resolved_rows) < 2:
            continue

        for idx in range(1, len(resolved_rows)):
            row = resolved_rows.iloc[idx]
            resolved_dt = row["StartTime"]
            if isinstance(resolved_dt, pd.Timestamp):
                resolved_dt = resolved_dt.to_pydatetime()

            if not isinstance(resolved_dt, datetime):
                continue

            if range_start is not None and resolved_dt < range_start:
                continue
            if range_end is not None and resolved_dt > range_end:
                continue

            prev_row = resolved_rows.iloc[idx - 1]
            country = (
                str(row["Country"]).strip()
                if has_country
                and "Country" in row.index
                and pd.notna(row["Country"])
                else ""
            )

            results.append(
                {
                    "case_number": case_number,
                    "resolved_date": prev_row["StartTime"],
                    "reopen_date": resolved_dt,
                    "agent": row["Email"],
                    "detection_type": "reopen_por_resolved_en_rango_v2",
                    "post_resolved_new_value": RESOLVED_VALUE,
                    "country": country,
                }
            )

    if not results:
        return empty

    return pd.DataFrame(results)
