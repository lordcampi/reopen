"""Filtering module — filters reopen results by reopen_date range."""

from datetime import datetime

import pandas as pd


def filter_by_reopen_date(
    df: pd.DataFrame,
    start_date: datetime | None,
    end_date: datetime | None,
) -> pd.DataFrame:
    """Filter reopen results by reopen_date range.

    Args:
        df: DataFrame with reopen detection results (must have reopen_date column).
        start_date: Start of date range (inclusive). None means no lower bound.
        end_date: End of date range (inclusive). None means no upper bound.

    Returns:
        Filtered DataFrame.
    """
    if df.empty:
        return df

    filtered = df.copy()

    if start_date is not None:
        filtered = filtered[filtered["reopen_date"] >= pd.Timestamp(start_date)]

    if end_date is not None:
        # Set end_date to end of day for inclusive filtering
        end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[filtered["reopen_date"] <= end_ts]

    return filtered