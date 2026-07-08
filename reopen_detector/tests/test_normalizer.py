"""Tests for normalizer module."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.normalizer import normalize_dataframe


def test_spanish_month_parsing():
    """Test that dates with Spanish months are parsed correctly."""
    df = pd.DataFrame(
        {
            "StartTime": ["7 jul 2026, 8:13:41", "5 jul 2026, 12:36:29"],
            "NewValue": ["Open", "In Progress"],
            "Email": ["agent1@example.com", "agent2@example.com"],
            "case_number": ["CASE-001", "CASE-001"],
        }
    )

    result, invalid = normalize_dataframe(df)

    assert invalid == 0
    assert len(result) == 2

    # After sorting by StartTime, the earliest date (day 5) comes first
    first_row = result.iloc[0]
    second_row = result.iloc[1]

    assert pd.notna(first_row["StartTime"])
    assert pd.notna(second_row["StartTime"])

    # First row should be July 5, second should be July 7
    assert first_row["StartTime"].month == 7
    assert first_row["StartTime"].day == 5
    assert first_row["StartTime"].year == 2026

    assert second_row["StartTime"].month == 7
    assert second_row["StartTime"].day == 7
    assert second_row["StartTime"].year == 2026


def test_invalid_starttime_handled():
    """Test that rows with invalid StartTime are dropped."""
    df = pd.DataFrame(
        {
            "StartTime": ["2026-07-01 10:00:00", "not_a_date", "2026-07-02 10:00:00"],
            "NewValue": ["Open", "Open", "Open"],
            "Email": ["a@b.com", "c@d.com", "e@f.com"],
            "case_number": ["CASE-001", "CASE-001", "CASE-001"],
        }
    )

    result, invalid = normalize_dataframe(df)

    assert invalid >= 1
    assert len(result) == 2


def test_newvalue_normalization():
    """Test that NewValue is normalized to lowercase and nulls are cleaned."""
    df = pd.DataFrame(
        {
            "StartTime": ["2026-07-01 10:00:00", "2026-07-01 11:00:00"],
            "NewValue": ["RESOLVED", "null"],
            "Email": ["a@b.com", "a@b.com"],
            "case_number": ["CASE-001", "CASE-001"],
        }
    )

    result, invalid = normalize_dataframe(df)

    assert result.loc[result.index[0], "NewValue"] == "resolved"
    assert result.loc[result.index[1], "NewValue"] == ""


def test_empty_values_normalized():
    """Test that None, nan, and empty strings are normalized."""
    df = pd.DataFrame(
        {
            "StartTime": [
                "2026-07-01 10:00:00",
                "2026-07-01 11:00:00",
                "2026-07-01 12:00:00",
            ],
            "NewValue": ["None", "nan", ""],
            "Email": ["a@b.com", "a@b.com", "a@b.com"],
            "case_number": ["CASE-001", "CASE-001", "CASE-001"],
        }
    )

    result, invalid = normalize_dataframe(df)

    for i in range(3):
        assert result.loc[result.index[i], "NewValue"] == ""


def test_email_normalized():
    """Test that Email is trimmed and lowercased."""
    df = pd.DataFrame(
        {
            "StartTime": ["2026-07-01 10:00:00"],
            "NewValue": ["Open"],
            "Email": ["  Agent1@Example.COM  "],
            "case_number": ["CASE-001"],
        }
    )

    result, invalid = normalize_dataframe(df)

    assert result.loc[result.index[0], "Email"] == "agent1@example.com"


def test_case_number_as_string():
    """Test that case_number is treated as string."""
    df = pd.DataFrame(
        {
            "StartTime": ["2026-07-01 10:00:00"],
            "NewValue": ["Open"],
            "Email": ["a@b.com"],
            "case_number": [12345],
        }
    )

    result, invalid = normalize_dataframe(df)

    assert result.loc[result.index[0], "case_number"] == "12345"


def test_sorted_by_case_and_time():
    """Test that output is sorted by case_number and StartTime."""
    df = pd.DataFrame(
        {
            "StartTime": [
                "2026-07-01 14:00:00",
                "2026-07-01 10:00:00",
                "2026-07-01 09:00:00",
            ],
            "NewValue": ["Open", "Resolved", "Open"],
            "Email": ["a@b.com", "a@b.com", "b@c.com"],
            "case_number": ["CASE-001", "CASE-001", "CASE-002"],
        }
    )

    result, invalid = normalize_dataframe(df)

    # CASE-001 should come before CASE-002
    assert result.loc[result.index[0], "case_number"] == "CASE-001"
    assert result.loc[result.index[1], "case_number"] == "CASE-001"
    assert result.loc[result.index[2], "case_number"] == "CASE-002"

    # Within CASE-001, earliest should be first
    case001 = result[result["case_number"] == "CASE-001"]
    assert case001.iloc[0]["StartTime"] < case001.iloc[1]["StartTime"]