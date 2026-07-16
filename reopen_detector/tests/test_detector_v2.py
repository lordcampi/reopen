"""Tests for V2 reopen detection."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.detector_v2 import detect_reopens_v2
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
    assert filtered.iloc[0]["detection_type"] == "reopen_por_resolved_en_rango_v2"
    assert filtered["reopen_date"].tolist() == sorted(
        filtered["reopen_date"].tolist()
    )


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


def test_resolved_outside_range_excluded():
    df = _build_df(
        [
            {
                "StartTime": "2026-06-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-05 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-20 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens_v2(
        df, start_date=date(2026, 7, 6), end_date=date(2026, 7, 12)
    )
    assert len(result) == 0


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
