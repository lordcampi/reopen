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