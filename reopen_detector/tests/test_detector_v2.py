"""Tests for V2 reopen detection."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.detector_v2 import (
    DETECTION_TYPE_OPEN_CYCLE_PROXY_V2,
    DETECTION_TYPE_V2,
    detect_reopens_v2,
)
from reopen_detector.filters import filter_by_reopen_date
from reopen_detector.normalizer import normalize_dataframe


def _build_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df, _ = normalize_dataframe(df)
    return df


def test_multiple_resolved_in_range_one_row_each():
    """Each Resolved after the first, within range, counts as one reopen."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-25 08:57:33",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "348917008",
            },
            {
                "StartTime": "2026-07-09 08:43:49",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "348917008",
            },
            {
                "StartTime": "2026-07-10 08:17:23",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "348917008",
            },
            {
                "StartTime": "2026-07-11 09:04:05",
                "NewValue": "Resolved",
                "Email": "agent4@example.com",
                "case_number": "348917008",
            },
            {
                "StartTime": "2026-07-12 09:59:54",
                "NewValue": "Resolved",
                "Email": "agent5@example.com",
                "case_number": "348917008",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    filtered = filter_by_reopen_date(
        result, date(2026, 7, 6), date(2026, 7, 12)
    )

    assert len(filtered) == 4
    assert filtered["case_number"].nunique() == 1
    assert filtered.iloc[0]["detection_type"] == DETECTION_TYPE_V2
    assert filtered["reopen_date"].tolist() == sorted(
        filtered["reopen_date"].tolist()
    )


def test_resolved_outside_range_plus_one_inside_counts_one():
    """One Resolved outside range + one inside → 1 reopen in period."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-08 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )

    assert len(result) == 1
    assert result.iloc[0]["case_number"] == "CASE-001"
    assert result.iloc[0]["detection_type"] == DETECTION_TYPE_V2


def test_multiple_in_range_skips_first_historical_even_if_also_in_range():
    """First historical Resolved in range is not counted; later ones are."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-07 09:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-002",
            },
            {
                "StartTime": "2026-07-09 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-002",
            },
            {
                "StartTime": "2026-07-11 11:00:00",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "CASE-002",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )

    assert len(result) == 2
    assert result["reopen_date"].tolist() == sorted(result["reopen_date"].tolist())


def test_first_resolved_in_range_not_counted_without_prior():
    """Only one Resolved total → no reopen rows."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-10 08:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-NEW",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    assert len(result) == 0


def test_single_resolved_with_non_resolved_activity_not_counted():
    """One Resolved + In Progress in range → 0 reopens (Resolved-only rule)."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-003",
            },
            {
                "StartTime": "2026-07-08 12:00:00",
                "NewValue": "In Progress",
                "Email": "agent2@example.com",
                "case_number": "CASE-003",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    assert len(result) == 0


def test_resolved_outside_range_excluded():
    df = _build_df(
        [
            {
                "StartTime": "2026-06-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-004",
            },
            {
                "StartTime": "2026-07-05 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-004",
            },
            {
                "StartTime": "2026-07-20 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "CASE-004",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    assert len(result) == 0


def test_defensive_dedup_same_case_and_starttime():
    """Identical Resolved rows must not inflate the reopen count."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-DEDUP",
            },
            {
                "StartTime": "2026-07-08 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-DEDUP",
            },
            {
                "StartTime": "2026-07-08 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-DEDUP",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    assert len(result) == 1


def test_case_348917008_from_sample_csv():
    csv_path = (
        Path(__file__).parent.parent
        / "Xtendo - Resultados_Gestiones Off SF_Tabla (3).csv"
    )
    if not csv_path.exists():
        return

    raw = pd.read_csv(csv_path)
    df, _ = normalize_dataframe(raw)

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    filtered = filter_by_reopen_date(
        result, date(2026, 7, 6), date(2026, 7, 12)
    )
    case_rows = filtered[filtered["case_number"] == "348917008"]

    assert len(case_rows) == 4


def test_open_cycle_proxy_349439940_pattern():
    """Resolved before range + activity in range + Resolved after → Tipo B."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-03 17:27:42",
                "NewValue": "Resolved",
                "Email": "alejandro@example.com",
                "case_number": "349439940",
            },
            {
                "StartTime": "2026-07-06 11:25:04",
                "NewValue": "null",
                "Email": "cesar@example.com",
                "case_number": "349439940",
            },
            {
                "StartTime": "2026-07-13 08:38:18",
                "NewValue": "Resolved",
                "Email": "cesar@example.com",
                "case_number": "349439940",
            },
        ]
    )

    result = detect_reopens_v2(
        df,
        start_date=date(2026, 7, 6),
        end_date=date(2026, 7, 12),
        enable_open_cycle_proxy=True,
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["case_number"] == "349439940"
    assert row["detection_type"] == DETECTION_TYPE_OPEN_CYCLE_PROXY_V2
    assert row["reopen_date"] == pd.Timestamp("2026-07-06 11:25:04")


def test_open_cycle_proxy_disabled_returns_zero_for_349439940_pattern():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-03 17:27:42",
                "NewValue": "Resolved",
                "Email": "alejandro@example.com",
                "case_number": "349439940",
            },
            {
                "StartTime": "2026-07-06 11:25:04",
                "NewValue": "null",
                "Email": "cesar@example.com",
                "case_number": "349439940",
            },
            {
                "StartTime": "2026-07-13 08:38:18",
                "NewValue": "Resolved",
                "Email": "cesar@example.com",
                "case_number": "349439940",
            },
        ]
    )

    result = detect_reopens_v2(
        df,
        start_date=date(2026, 7, 6),
        end_date=date(2026, 7, 12),
        enable_open_cycle_proxy=False,
    )
    assert len(result) == 0


def test_open_cycle_proxy_not_added_when_type_a_already_counts():
    """If Tipo A already counts a Resolved in range, do not add Tipo B."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-NO-DOUBLE",
            },
            {
                "StartTime": "2026-07-07 09:00:00",
                "NewValue": "null",
                "Email": "agent2@example.com",
                "case_number": "CASE-NO-DOUBLE",
            },
            {
                "StartTime": "2026-07-10 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "CASE-NO-DOUBLE",
            },
        ]
    )

    result = detect_reopens_v2(
        df,
        start_date=date(2026, 7, 6),
        end_date=date(2026, 7, 12),
        enable_open_cycle_proxy=True,
    )

    assert len(result) == 1
    assert result.iloc[0]["detection_type"] == DETECTION_TYPE_V2
    assert DETECTION_TYPE_OPEN_CYCLE_PROXY_V2 not in result["detection_type"].tolist()


def test_case_349439940_from_csv4_if_present():
    csv_path = Path.home() / "Downloads" / "Xtendo - Resultados_Gestiones Off SF_Tabla (4).csv"
    if not csv_path.exists():
        return

    raw = pd.read_csv(csv_path)
    df, _ = normalize_dataframe(raw)

    result = detect_reopens_v2(
        df,
        start_date=date(2026, 7, 6),
        end_date=date(2026, 7, 12),
        enable_open_cycle_proxy=True,
    )
    filtered = filter_by_reopen_date(
        result, date(2026, 7, 6), date(2026, 7, 12)
    )
    case_rows = filtered[filtered["case_number"].astype(str) == "349439940"]

    assert len(case_rows) == 1
    assert (
        case_rows.iloc[0]["detection_type"] == DETECTION_TYPE_OPEN_CYCLE_PROXY_V2
    )
