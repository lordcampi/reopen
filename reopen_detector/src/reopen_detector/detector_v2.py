"""V2 reopen detection — duplicate Resolved events per case."""

from datetime import date, datetime, time

import pandas as pd

from reopen_detector.config import RESOLVED_VALUE

# Set to False to restore previous V2 behavior (Tipo A only).
ENABLE_OPEN_CYCLE_PROXY_V2 = True

DETECTION_TYPE_V2 = "reopen_por_resolved_duplicado_v2"
DETECTION_TYPE_OPEN_CYCLE_PROXY_V2 = "reopen_por_actividad_post_resolved_v2"

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


def _row_country(row: pd.Series, has_country: bool) -> str:
    if (
        has_country
        and "Country" in row.index
        and pd.notna(row["Country"])
    ):
        return str(row["Country"]).strip()
    return ""


def _detect_resolved_duplicates_v2(
    resolved_rows: pd.DataFrame,
    range_start: datetime | None,
    range_end: datetime | None,
) -> list[dict]:
    """Tipo A: each Resolved after the first whose StartTime is in range."""
    has_country = "Country" in resolved_rows.columns
    results: list[dict] = []

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
            results.append(
                {
                    "case_number": case_number,
                    "resolved_date": prev_row["StartTime"],
                    "reopen_date": resolved_dt,
                    "agent": row["Email"],
                    "detection_type": DETECTION_TYPE_V2,
                    "post_resolved_new_value": RESOLVED_VALUE,
                    "country": _row_country(row, has_country),
                }
            )

    return results


def _detect_open_cycle_proxy_v2(
    df: pd.DataFrame,
    resolved_rows: pd.DataFrame,
    range_start: datetime | None,
    range_end: datetime | None,
    type_a_case_numbers: set,
) -> list[dict]:
    """Tipo B: reopen proxy when next Resolved falls after the range.

    Conditions:
    1. Case has >= 2 Resolved total.
    2. There is a Resolved before range_start.
    3. First interaction after that closure has StartTime in range.
    4. There is another Resolved after that activity (may be outside range).
    5. Case was not already counted by Tipo A in this range.
    """
    if range_start is None:
        return []

    has_country = "Country" in df.columns
    results: list[dict] = []

    for case_number, case_resolved in resolved_rows.groupby("case_number"):
        if case_number in type_a_case_numbers:
            continue

        case_resolved = case_resolved.reset_index(drop=True)
        if len(case_resolved) < 2:
            continue

        prior_resolved = None
        for _, row in case_resolved.iterrows():
            dt = _to_datetime(row["StartTime"])
            if dt is None:
                continue
            if dt < range_start:
                prior_resolved = row
            else:
                break

        if prior_resolved is None:
            continue

        prior_dt = _to_datetime(prior_resolved["StartTime"])
        if prior_dt is None:
            continue

        case_rows = (
            df[df["case_number"] == case_number]
            .sort_values(by="StartTime")
            .reset_index(drop=True)
        )

        first_after = None
        first_after_dt = None
        for _, row in case_rows.iterrows():
            dt = _to_datetime(row["StartTime"])
            if dt is None:
                continue
            if dt > prior_dt:
                first_after = row
                first_after_dt = dt
                break

        if first_after is None or first_after_dt is None:
            continue
        if not _is_in_range(first_after_dt, range_start, range_end):
            continue

        has_later_resolved = False
        for _, row in case_resolved.iterrows():
            dt = _to_datetime(row["StartTime"])
            if dt is not None and dt > first_after_dt:
                has_later_resolved = True
                break

        if not has_later_resolved:
            continue

        results.append(
            {
                "case_number": case_number,
                "resolved_date": prior_resolved["StartTime"],
                "reopen_date": first_after_dt,
                "agent": first_after["Email"],
                "detection_type": DETECTION_TYPE_OPEN_CYCLE_PROXY_V2,
                "post_resolved_new_value": first_after["NewValue"],
                "country": _row_country(first_after, has_country),
            }
        )

    return results


def detect_reopens_v2(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    enable_open_cycle_proxy: bool | None = None,
) -> pd.DataFrame:
    """Detect reopen cycles for V2 range analysis.

    Business rule:
    1. A healthy case should have only one ``Resolved`` in the full CSV.
    2. Each additional ``Resolved`` for the same case is a duplicate closure
       (reopen cycle).
    3. Only duplicate closures whose ``StartTime`` falls within the query
       range are counted for period metrics (Tipo A).
    4. Optionally (Tipo B / open-cycle proxy): if a Resolved exists before the
       range, the first post-closure interaction falls inside the range, and a
       later Resolved exists (even outside the range), emit +1 reopen. Disabled
       when ``ENABLE_OPEN_CYCLE_PROXY_V2`` is False.

    Args:
        df: Normalized DataFrame sorted by case_number and StartTime.
        start_date: Optional inclusive start date (UY local).
        end_date: Optional inclusive end date (UY local).
        start_time: Optional start time of day (defaults to 00:00:00).
        end_time: Optional end time of day (defaults to 23:59:59).
        enable_open_cycle_proxy: Override for the module flag. ``None`` uses
            ``ENABLE_OPEN_CYCLE_PROXY_V2``.

    Returns:
        DataFrame with the same columns as ``detect_reopens``.
    """
    if start_date is None and end_date is None:
        return _empty_result()

    use_proxy = (
        ENABLE_OPEN_CYCLE_PROXY_V2
        if enable_open_cycle_proxy is None
        else enable_open_cycle_proxy
    )

    range_start, range_end = _build_range_bounds(
        start_date, end_date, start_time, end_time
    )
    resolved_rows = _extract_resolved_rows(df)
    if resolved_rows.empty:
        return _empty_result()

    type_a = _detect_resolved_duplicates_v2(
        resolved_rows, range_start, range_end
    )
    results = list(type_a)

    if use_proxy:
        type_a_cases = {row["case_number"] for row in type_a}
        type_b = _detect_open_cycle_proxy_v2(
            df,
            resolved_rows,
            range_start,
            range_end,
            type_a_cases,
        )
        results.extend(type_b)

    if not results:
        return _empty_result()

    return pd.DataFrame(results)


def build_all_reopens_v2(
    df: pd.DataFrame,
    enable_open_cycle_proxy: bool | None = None,
) -> pd.DataFrame:
    """Build reopen rows for every ISO week overlapping the data span.

    Runs ``detect_reopens_v2`` once per ISO week so weekly comparison matches
    Análisis por rango for the same calendar bounds (Tipo A + Tipo B).
    """
    if df.empty or "StartTime" not in df.columns:
        return _empty_result()

    start_times = pd.to_datetime(df["StartTime"]).dropna()
    if start_times.empty:
        return _empty_result()

    min_ts = start_times.min()
    max_ts = start_times.max()
    min_date = min_ts.date() if hasattr(min_ts, "date") else min_ts
    max_date = max_ts.date() if hasattr(max_ts, "date") else max_ts

    min_iso = min_date.isocalendar()
    max_iso = max_date.isocalendar()
    years = range(int(min_iso.year), int(max_iso.year) + 1)

    frames: list[pd.DataFrame] = []
    for year in years:
        max_week = date(year, 12, 28).isocalendar().week
        for week in range(1, max_week + 1):
            week_start = date.fromisocalendar(year, week, 1)
            week_end = date.fromisocalendar(year, week, 7)
            if week_end < min_date or week_start > max_date:
                continue

            week_reopens = detect_reopens_v2(
                df,
                start_date=week_start,
                end_date=week_end,
                enable_open_cycle_proxy=enable_open_cycle_proxy,
            )
            if not week_reopens.empty:
                frames.append(week_reopens)

    if not frames:
        return _empty_result()

    return pd.concat(frames, ignore_index=True)
