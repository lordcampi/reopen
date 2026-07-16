"""V2 reopen detection — duplicate Resolved events per case."""

from datetime import date, datetime, time

import pandas as pd

from reopen_detector.config import RESOLVED_VALUE

DETECTION_TYPE_V2 = "reopen_por_resolved_duplicado_v2"

RESULT_COLUMNS = [
    "case_number",
    "resolved_date",
    "reopen_date",
    "agent",
    "detection_type",
    "post_resolved_new_value",
    "country",
]


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def _build_range_bounds(
    start_date: date | None,
    end_date: date | None,
    start_time: time | None,
    end_time: time | None,
) -> tuple[datetime | None, datetime | None]:
    st = start_time if start_time is not None else time(0, 0)
    et = end_time if end_time is not None else time(23, 59, 59)
    range_start = datetime.combine(start_date, st) if start_date is not None else None
    range_end = datetime.combine(end_date, et) if end_date is not None else None
    return range_start, range_end


def _to_datetime(value) -> datetime | None:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return None


def _is_in_range(
    dt: datetime,
    range_start: datetime | None,
    range_end: datetime | None,
) -> bool:
    if range_start is not None and dt < range_start:
        return False
    if range_end is not None and dt > range_end:
        return False
    return True


def _extract_resolved_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline step 1–3: filter Resolved, dedup, sort."""
    resolved = df[df["NewValue"] == RESOLVED_VALUE].copy()
    if resolved.empty:
        return resolved

    resolved = resolved.drop_duplicates(
        subset=["case_number", "StartTime"],
        keep="first",
    )
    return resolved.sort_values(by=["case_number", "StartTime"]).reset_index(drop=True)


def detect_reopens_v2(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> pd.DataFrame:
    """Detect reopen cycles for V2 range analysis.

    Business rule:
    1. A healthy case should have only one ``Resolved`` in the full CSV.
    2. Each additional ``Resolved`` for the same case is a duplicate closure
       (reopen cycle).
    3. Only duplicate closures whose ``StartTime`` falls within the query
       range are counted for period metrics.

    Pipeline:
    1. Filter ``NewValue == resolved``
    2. Deduplicate by ``(case_number, StartTime)``
    3. Sort by ``case_number``, ``StartTime``
    4. Skip the first ``Resolved`` per case (initial closure, not a reopen)
    5. Emit one row per duplicate ``Resolved`` whose ``StartTime`` is in range

    Args:
        df: Normalized DataFrame sorted by case_number and StartTime.
        start_date: Optional inclusive start date (UY local).
        end_date: Optional inclusive end date (UY local).
        start_time: Optional start time of day (defaults to 00:00:00).
        end_time: Optional end time of day (defaults to 23:59:59).

    Returns:
        DataFrame with the same columns as ``detect_reopens``.
    """
    if start_date is None and end_date is None:
        return _empty_result()

    range_start, range_end = _build_range_bounds(
        start_date, end_date, start_time, end_time
    )
    resolved_rows = _extract_resolved_rows(df)
    if resolved_rows.empty:
        return _empty_result()

    has_country = "Country" in resolved_rows.columns
    results = []

    for case_number, case_resolved in resolved_rows.groupby("case_number"):
        case_resolved = case_resolved.reset_index(drop=True)
        if len(case_resolved) < 2:
            continue

        for idx in range(1, len(case_resolved)):
            row = case_resolved.iloc[idx]
            resolved_dt = _to_datetime(row["StartTime"])
            if resolved_dt is None:
                continue
            if not _is_in_range(resolved_dt, range_start, range_end):
                continue

            prev_row = case_resolved.iloc[idx - 1]
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
                    "detection_type": DETECTION_TYPE_V2,
                    "post_resolved_new_value": RESOLVED_VALUE,
                    "country": country,
                }
            )

    if not results:
        return _empty_result()

    return pd.DataFrame(results)
