"""Tests for the detector module — all 10 mandatory test cases."""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.detector import detect_reopens
from reopen_detector.normalizer import normalize_dataframe


def _build_df(records: list[dict]) -> pd.DataFrame:
    """Helper to build and normalize a test DataFrame."""
    df = pd.DataFrame(records)
    df, _ = normalize_dataframe(df)
    return df


# Test 1: Case without Resolved -> no reopen
def test_no_resolved_no_reopen():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 11:00:00",
                "NewValue": "In Progress",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 0


# Test 2: Case with Resolved and no subsequent event -> no reopen
def test_resolved_no_subsequent_no_reopen():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 0


# Test 3: Resolved + null -> reopen_confirmado
def test_resolved_then_null_reopen_confirmado():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "null",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["detection_type"] == "reopen_confirmado"
    assert row["agent"] == "agent2@example.com"
    assert row["case_number"] == "CASE-001"


# Test 4: Resolved + In Progress -> reopen_confirmado
def test_resolved_then_in_progress_reopen_confirmado():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "In Progress",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["detection_type"] == "reopen_confirmado"
    assert row["agent"] == "agent2@example.com"


# Test 5: Resolved + Resolved -> reopen_por_resolved_multiple
def test_resolved_then_resolved_multiple():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["detection_type"] == "reopen_por_resolved_multiple"
    assert row["agent"] == "agent2@example.com"


# Test 6: Events before Resolved do not count as reopen
def test_events_before_resolved_dont_count():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 11:00:00",
                "NewValue": "In Progress",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 12:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    # Resolved is the last event, so no reopen (no subsequent interaction)
    assert len(result) == 0


# Test 7: Multiple subsequent events — take only the first
def test_multiple_subsequent_take_first():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "In Progress",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-02 08:00:00",
                "NewValue": "Open",
                "Email": "agent3@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    # reopen_date should be the first subsequent interaction (16:00, not 08:00 next day)
    assert row["agent"] == "agent2@example.com"
    assert row["post_resolved_new_value"] == "in progress"


# Test 8: Agent is Email of the subsequent event
def test_agent_is_subsequent_email():
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "original@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "resolver@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "Open",
                "Email": "reopener@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["agent"] == "reopener@example.com"
    # Should not be the resolver's email
    assert row["agent"] != "resolver@example.com"


# Test 9: Invalid StartTime should not break execution
def test_invalid_starttime_no_break():
    """Rows with invalid StartTime should be dropped during normalization
    without breaking detection."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 16:00:00",
                "NewValue": "In Progress",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "not_valid_date",
                "NewValue": "Open",
                "Email": "agent3@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    # Should work fine — invalid row dropped, detection runs on remaining
    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["detection_type"] == "reopen_confirmado"
    assert row["agent"] == "agent2@example.com"


# Test 10: Filter should use reopen_date
def test_reopen_date_is_correct():
    """Verify that reopen_date is the StartTime of the subsequent interaction."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-01 10:00:00",
                "NewValue": "Open",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-01 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-05 09:00:00",
                "NewValue": "In Progress",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    result = detect_reopens(df)
    assert len(result) == 1
    row = result.iloc[0]

    # reopen_date should be the StartTime of the subsequent event
    expected_reopen = pd.Timestamp("2026-07-05 09:00:00")
    assert row["reopen_date"] == expected_reopen


# ---------------------------------------------------------------------------
# Tests for Strategy 3: reopen_por_resolved_en_rango
# ---------------------------------------------------------------------------


def test_resolved_en_rango_detected():
    """Case with >=2 Resolved, at least one in query range → detected."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-20 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-001",
            },
            {
                "StartTime": "2026-07-05 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-001",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    # Should have the standard detection (Strategy 2) AND the new one
    types = result["detection_type"].tolist()
    assert "reopen_por_resolved_en_rango" in types

    # Verify the new detection row
    row = result[result["detection_type"] == "reopen_por_resolved_en_rango"].iloc[0]
    assert row["case_number"] == "CASE-001"
    assert row["agent"] == "agent2@example.com"  # agent of the in-range resolved


def test_resolved_en_rango_none_in_range_not_detected():
    """Case with >=2 Resolved, but NONE in query range → NOT detected by Strategy 3."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-10 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-002",
            },
            {
                "StartTime": "2026-06-15 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-002",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    # Strategy 3 should NOT appear
    types = result["detection_type"].tolist()
    assert "reopen_por_resolved_en_rango" not in types


def test_resolved_en_rango_single_resolved_not_detected():
    """Only 1 Resolved total → NOT enough for Strategy 3."""
    df = _build_df(
        [
            {
                "StartTime": "2026-07-05 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-003",
            },
            {
                "StartTime": "2026-07-06 10:00:00",
                "NewValue": "In Progress",
                "Email": "agent1@example.com",
                "case_number": "CASE-003",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    types = result["detection_type"].tolist()
    assert "reopen_por_resolved_en_rango" not in types


def test_resolved_en_rango_only_start_date():
    """Only start_date provided → resolved on or after that date counts as in-range."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-004",
            },
            {
                "StartTime": "2026-08-15 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-004",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=date(2026, 7, 1), end_date=None)

    types = result["detection_type"].tolist()
    assert "reopen_por_resolved_en_rango" in types


def test_resolved_en_rango_only_end_date():
    """Only end_date provided → resolved on or before that date counts as in-range."""
    df = _build_df(
        [
            {
                "StartTime": "2026-05-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-005",
            },
            {
                "StartTime": "2026-06-15 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-005",
            },
            {
                "StartTime": "2026-08-01 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent3@example.com",
                "case_number": "CASE-005",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=None, end_date=date(2026, 6, 30))

    types = result["detection_type"].tolist()
    assert "reopen_por_resolved_en_rango" in types


def test_resolved_en_rango_no_date_params():
    """Without date parameters, Strategy 3 is not applied (backward compatible)."""
    df = _build_df(
        [
            {
                "StartTime": "2026-06-20 10:00:00",
                "NewValue": "Resolved",
                "Email": "agent1@example.com",
                "case_number": "CASE-006",
            },
            {
                "StartTime": "2026-07-05 14:00:00",
                "NewValue": "Resolved",
                "Email": "agent2@example.com",
                "case_number": "CASE-006",
            },
        ]
    )

    result = detect_reopens(df)

    types = result["detection_type"].tolist()
    # Strategy 3 should not appear when no dates are given
    assert "reopen_por_resolved_en_rango" not in types
    # But Strategy 2 should still work
    assert "reopen_por_resolved_multiple" in types


def test_resolved_en_rango_resolved_date_is_first_in_history():
    """The resolved_date in the result should be the first resolved in history."""
    df = _build_df(
        [
            {
                "StartTime": "2026-05-10 08:00:00",
                "NewValue": "Resolved",
                "Email": "agent_old@example.com",
                "case_number": "CASE-007",
            },
            {
                "StartTime": "2026-07-10 12:00:00",
                "NewValue": "Resolved",
                "Email": "agent_new@example.com",
                "case_number": "CASE-007",
            },
        ]
    )

    from datetime import date

    result = detect_reopens(df, start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    row = result[result["detection_type"] == "reopen_por_resolved_en_rango"].iloc[0]
    expected_resolved_date = pd.Timestamp("2026-05-10 08:00:00")
    assert row["resolved_date"] == expected_resolved_date
    # reopen_date should be the first resolved within range
    expected_reopen_date = pd.Timestamp("2026-07-10 12:00:00")
    assert row["reopen_date"] == expected_reopen_date
