"""Tests for the weekly_analytics module."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.weekly_analytics import (
    build_week_catalog,
    build_weekly_comparison_donut,
    compare_weeks,
    count_reopens_in_week,
    format_delta_pct,
    format_week_label,
    get_available_years,
    weekly_totals_for_year,
)


def _build_reopens_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def test_format_week_label():
    start = date(2026, 3, 16)
    end = date(2026, 3, 22)
    label = format_week_label(2026, 12, start, end)
    assert label == "Semana 12 (16 mar – 22 mar 2026)"


def test_build_week_catalog_has_iso_weeks():
    catalog = build_week_catalog(2026)
    assert catalog[0]["week"] == 1
    assert catalog[-1]["week"] >= 52
    assert catalog[0]["start"].weekday() == 0
    assert catalog[0]["end"].weekday() == 6
    assert catalog[0]["short_label"] == "Semana 1"


def test_get_available_years_from_reopen_dates():
    df = _build_reopens_df(
        [
            {"case_number": "A", "reopen_date": pd.Timestamp("2025-12-29 10:00:00")},
            {"case_number": "B", "reopen_date": pd.Timestamp("2026-01-05 11:00:00")},
            {"case_number": "C", "reopen_date": pd.Timestamp("2026-07-10 09:00:00")},
        ]
    )
    years = get_available_years(df)
    assert years == [2026]


def test_count_reopens_in_week():
    df = _build_reopens_df(
        [
            {"case_number": "A", "reopen_date": pd.Timestamp("2026-07-06 10:00:00")},
            {"case_number": "A", "reopen_date": pd.Timestamp("2026-07-07 11:00:00")},
            {"case_number": "B", "reopen_date": pd.Timestamp("2026-07-08 12:00:00")},
            {"case_number": "C", "reopen_date": pd.Timestamp("2026-07-20 08:00:00")},
        ]
    )

    week_28 = count_reopens_in_week(df, 2026, 28)
    week_30 = count_reopens_in_week(df, 2026, 30)

    assert week_28["total"] == 3
    assert week_28["unique_cases"] == 2
    assert week_30["total"] == 1
    assert week_30["unique_cases"] == 1


def test_compare_weeks_delta():
    df = _build_reopens_df(
        [
            {"case_number": "A", "reopen_date": pd.Timestamp("2026-07-06 10:00:00")},
            {"case_number": "B", "reopen_date": pd.Timestamp("2026-07-07 11:00:00")},
            {"case_number": "C", "reopen_date": pd.Timestamp("2026-07-20 08:00:00")},
            {"case_number": "D", "reopen_date": pd.Timestamp("2026-07-21 09:00:00")},
            {"case_number": "E", "reopen_date": pd.Timestamp("2026-07-22 10:00:00")},
        ]
    )

    comparison = compare_weeks(df, 2026, 28, 30)

    assert comparison["week_a"]["total"] == 2
    assert comparison["week_b"]["total"] == 3
    assert comparison["delta_total"] == 1
    assert comparison["delta_pct"] == 50.0


def test_weekly_totals_for_year_shape():
    df = _build_reopens_df(
        [
            {"case_number": "A", "reopen_date": pd.Timestamp("2026-01-05 10:00:00")},
            {"case_number": "B", "reopen_date": pd.Timestamp("2026-07-06 10:00:00")},
        ]
    )

    totals = weekly_totals_for_year(df, 2026)
    assert len(totals) == build_week_catalog(2026)[-1]["week"]
    assert totals.loc[totals["week"] == 2, "total"].iloc[0] == 1
    assert totals.loc[totals["week"] == 28, "total"].iloc[0] == 1


def test_build_weekly_comparison_donut_has_two_segments():
    comparison = compare_weeks(
        _build_reopens_df(
            [
                {"case_number": "A", "reopen_date": pd.Timestamp("2026-07-06 10:00:00")},
                {"case_number": "B", "reopen_date": pd.Timestamp("2026-07-20 08:00:00")},
            ]
        ),
        2026,
        28,
        30,
    )

    fig = build_weekly_comparison_donut(comparison)
    assert len(fig.data) == 1
    assert list(fig.data[0].labels) == ["Semana 28", "Semana 30"]
    assert list(fig.data[0].values) == [1, 1]


def test_build_weekly_comparison_donut_zero_weeks():
    comparison = compare_weeks(_build_reopens_df([]), 2026, 1, 2)
    fig = build_weekly_comparison_donut(comparison)
    assert fig is not None
    assert len(fig.data[0].labels) == 2


def test_format_delta_pct():
    assert format_delta_pct(50.0) == "+50.0% vs Semana A"
    assert format_delta_pct(-25.0) == "-25.0% vs Semana A"
    assert format_delta_pct(None) == "Sin variación (base en 0)"
