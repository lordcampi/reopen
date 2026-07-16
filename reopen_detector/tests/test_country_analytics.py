"""Tests for the country_analytics module."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.country_analytics import (
    EMPTY_COUNTRY_LABEL,
    aggregate_reopens_by_country,
    build_country_donut_chart,
)


def _build_reopens_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


def test_aggregate_reopens_by_country_sorts_descending():
    df = _build_reopens_df(
        [
            {"country": "UY", "case_number": "A"},
            {"country": "AR", "case_number": "B"},
            {"country": "UY", "case_number": "C"},
            {"country": "BR", "case_number": "D"},
            {"country": "UY", "case_number": "E"},
        ]
    )

    result = aggregate_reopens_by_country(df)

    assert result.iloc[0]["country"] == "UY"
    assert result.iloc[0]["total"] == 3
    assert result.iloc[1]["country"] == "AR"
    assert result.iloc[2]["country"] == "BR"


def test_aggregate_reopens_by_country_empty_becomes_sin_pais():
    df = _build_reopens_df(
        [
            {"country": "", "case_number": "A"},
            {"country": None, "case_number": "B"},
            {"country": "AR", "case_number": "C"},
        ]
    )

    result = aggregate_reopens_by_country(df)

    sin_pais = result.loc[result["country"] == EMPTY_COUNTRY_LABEL, "total"].iloc[0]
    assert sin_pais == 2
    assert result.loc[result["country"] == "AR", "total"].iloc[0] == 1


def test_build_country_donut_chart_returns_none_when_empty():
    assert build_country_donut_chart(_build_reopens_df([])) is None


def test_build_country_donut_chart_has_segments():
    df = _build_reopens_df(
        [
            {"country": "UY", "case_number": "A"},
            {"country": "AR", "case_number": "B"},
            {"country": "UY", "case_number": "C"},
        ]
    )

    fig = build_country_donut_chart(df)
    assert fig is not None
    assert len(fig.data) == 1
    assert list(fig.data[0].labels) == ["UY", "AR"]
    assert list(fig.data[0].values) == [2, 1]
