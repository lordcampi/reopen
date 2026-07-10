"""Filtering module — filters reopen results by reopen_date range.

All times are interpreted in Uruguay local time (UTC-3).
Uruguay does not observe DST since 2015, so UTC-3 is permanent.
Comparisons are timezone-naive; the user is expected to input dates/times
in UY local time, matching the naive timestamps in the source data.
"""

from datetime import date, datetime, time

import pandas as pd


def filter_by_reopen_date(
    df: pd.DataFrame,
    start_date: date | None,
    end_date: date | None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> pd.DataFrame:
    """Filter reopen results by reopen_date range.

    Args:
        df: DataFrame with reopen detection results (must have reopen_date column).
        start_date: Start date (inclusive, UY local). None means no lower bound.
        end_date: End date (inclusive, UY local). None means no upper bound.
        start_time: Start time of day (UY local, defaults to 00:00:00).
        end_time: End time of day (UY local, defaults to 23:59:59).

    Returns:
        Filtered DataFrame.
    """
    if df.empty:
        return df

    filtered = df.copy()

    if start_date is not None:
        st = start_time if start_time is not None else time(0, 0)
        start_dt = datetime.combine(start_date, st)
        filtered = filtered[filtered["reopen_date"] >= pd.Timestamp(start_dt)]

    if end_date is not None:
        et = end_time if end_time is not None else time(23, 59, 59)
        end_dt = datetime.combine(end_date, et)
        filtered = filtered[filtered["reopen_date"] <= pd.Timestamp(end_dt)]

    return filtered
