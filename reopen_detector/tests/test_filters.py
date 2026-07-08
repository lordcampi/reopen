"""Tests for the filters module."""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.filters import filter_by_reopen_date


def _build_reopens_df(records: list[dict]) -> pd.DataFrame:
    """Helper to build a DataFrame that looks like detector output."""
    return pd.DataFrame(records)


def test_filter_by_reopen_date_inclusive():
    """Test that the filter includes boundaries."""
    df = _build_reopens_df(
        [
            {
                "case_number": "CASE-001",
                "resolved_date": pd.Timestamp("2026-07-01 14:00:00"),
                "reopen_date": pd.Timestamp("2026-07-02 10:00:00"),
                "agent": "agent1@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
            {
                "case_number": "CASE-002",
                "resolved_date": pd.Timestamp("2026-07-05 10:00:00"),
                "reopen_date": pd.Timestamp("2026-07-06 10:00:00"),
                "agent": "agent2@example.com",
                "detection_type": "reopen_por_resolved_multiple",
                "post_resolved_new_value": "resolved",
            },
            {
                "case_number": "CASE-003",
                "resolved_date": pd.Timestamp("2026-07-10 10:00:00"),
                "reopen_date": pd.Timestamp("2026-07-15 10:00:00"),
                "agent": "agent3@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "in progress",
            },
        ]
    )

    start = datetime(2026, 7, 2)
    end = datetime(2026, 7, 6)

    result = filter_by_reopen_date(df, start, end)

    # CASE-001 (07-02) and CASE-002 (07-06) should be included
    # CASE-003 (07-15) should be excluded
    assert len(result) == 2
    assert "CASE-001" in result["case_number"].values
    assert "CASE-002" in result["case_number"].values
    assert "CASE-003" not in result["case_number"].values


def test_filter_no_start_date():
    """Test filter with only end_date."""
    df = _build_reopens_df(
        [
            {
                "case_number": "CASE-001",
                "resolved_date": pd.Timestamp("2026-06-01 10:00:00"),
                "reopen_date": pd.Timestamp("2026-06-15 10:00:00"),
                "agent": "agent1@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
            {
                "case_number": "CASE-002",
                "resolved_date": pd.Timestamp("2026-07-01 10:00:00"),
                "reopen_date": pd.Timestamp("2026-07-05 10:00:00"),
                "agent": "agent2@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
        ]
    )

    end = datetime(2026, 6, 30)
    result = filter_by_reopen_date(df, None, end)

    assert len(result) == 1
    assert result.iloc[0]["case_number"] == "CASE-001"


def test_filter_no_end_date():
    """Test filter with only start_date."""
    df = _build_reopens_df(
        [
            {
                "case_number": "CASE-001",
                "resolved_date": pd.Timestamp("2026-06-01 10:00:00"),
                "reopen_date": pd.Timestamp("2026-06-15 10:00:00"),
                "agent": "agent1@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
            {
                "case_number": "CASE-002",
                "resolved_date": pd.Timestamp("2026-07-01 10:00:00"),
                "reopen_date": pd.Timestamp("2026-07-05 10:00:00"),
                "agent": "agent2@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
        ]
    )

    start = datetime(2026, 7, 1)
    result = filter_by_reopen_date(df, start, None)

    assert len(result) == 1
    assert result.iloc[0]["case_number"] == "CASE-002"


def test_filter_empty_df():
    """Test filter on empty DataFrame."""
    df = _build_reopens_df([])
    result = filter_by_reopen_date(
        df, datetime(2026, 7, 1), datetime(2026, 7, 31)
    )
    assert len(result) == 0


def test_filter_reopen_date_not_starttime():
    """Verify filter uses reopen_date, not StartTime from CSV."""
    df = _build_reopens_df(
        [
            {
                "case_number": "CASE-001",
                "resolved_date": pd.Timestamp("2026-07-01 10:00:00"),
                "reopen_date": pd.Timestamp("2026-07-10 10:00:00"),
                "agent": "agent1@example.com",
                "detection_type": "reopen_confirmado",
                "post_resolved_new_value": "open",
            },
        ]
    )

    # Filter to dates well after resolved_date but covering reopen_date
    start = datetime(2026, 7, 5)
    end = datetime(2026, 7, 15)
    result = filter_by_reopen_date(df, start, end)
    assert len(result) == 1

    # Filter to dates before reopen_date — should exclude it
    start2 = datetime(2026, 7, 1)
    end2 = datetime(2026, 7, 5)
    result2 = filter_by_reopen_date(df, start2, end2)
    # reopen_date is 2026-07-10 which is outside 2026-07-01 to 2026-07-05 range
    assert len(result2) == 0