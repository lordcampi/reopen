"""Weekly aggregation and comparison for reopen analytics."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go

from reopen_detector.chart_theme import (
    THEME_PRIMARY,
    THEME_SECONDARY,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    dark_chart_layout,
)

MONTHS_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def _format_short_date(value: date) -> str:
    return f"{value.day} {MONTHS_ES[value.month]}"


def format_week_label(year: int, week: int, start: date, end: date) -> str:
    """Build a human-readable label for an ISO week."""
    return (
        f"Semana {week} ({_format_short_date(start)} – "
        f"{_format_short_date(end)} {end.year})"
    )


def format_week_short_label(week: int) -> str:
    """Short label for chart legends."""
    return f"Semana {week}"


def _iso_parts(series: pd.Series) -> pd.DataFrame:
    iso = series.dt.isocalendar()
    return pd.DataFrame({"iso_year": iso.year, "iso_week": iso.week})


def get_available_years(reopens_df: pd.DataFrame) -> list[int]:
    """Return sorted ISO years present in reopen_date."""
    if reopens_df.empty or "reopen_date" not in reopens_df.columns:
        return [date.today().year]

    parts = _iso_parts(pd.to_datetime(reopens_df["reopen_date"]))
    years = sorted(parts["iso_year"].unique().astype(int).tolist())
    return years or [date.today().year]


def build_week_catalog(year: int) -> list[dict]:
    """Build ISO week metadata for a calendar year."""
    max_week = date(year, 12, 28).isocalendar().week
    catalog = []

    for week in range(1, max_week + 1):
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
        catalog.append(
            {
                "year": year,
                "week": week,
                "start": start,
                "end": end,
                "label": format_week_label(year, week, start, end),
                "short_label": format_week_short_label(week),
            }
        )

    return catalog


def _filter_by_iso_week(
    reopens_df: pd.DataFrame, year: int, week: int
) -> pd.DataFrame:
    if reopens_df.empty:
        return reopens_df.copy()

    df = reopens_df.copy()
    df["reopen_date"] = pd.to_datetime(df["reopen_date"])
    parts = _iso_parts(df["reopen_date"])
    mask = (parts["iso_year"] == year) & (parts["iso_week"] == week)
    return df.loc[mask]


def count_reopens_in_week(
    reopens_df: pd.DataFrame, year: int, week: int
) -> dict:
    """Count reopen events and unique cases for an ISO week."""
    week_df = _filter_by_iso_week(reopens_df, year, week)
    catalog = build_week_catalog(year)
    week_info = next(item for item in catalog if item["week"] == week)

    return {
        "year": year,
        "week": week,
        "label": week_info["label"],
        "short_label": week_info["short_label"],
        "start": week_info["start"],
        "end": week_info["end"],
        "total": len(week_df),
        "unique_cases": (
            week_df["case_number"].nunique() if not week_df.empty else 0
        ),
    }


def compare_weeks(
    reopens_df: pd.DataFrame, year: int, week_a: int, week_b: int
) -> dict:
    """Compare reopen counts between two ISO weeks."""
    week_a_data = count_reopens_in_week(reopens_df, year, week_a)
    week_b_data = count_reopens_in_week(reopens_df, year, week_b)

    delta_total = week_b_data["total"] - week_a_data["total"]
    delta_cases = week_b_data["unique_cases"] - week_a_data["unique_cases"]

    if week_a_data["total"] > 0:
        delta_pct = (delta_total / week_a_data["total"]) * 100
    else:
        delta_pct = None if week_b_data["total"] == 0 else 100.0

    return {
        "week_a": week_a_data,
        "week_b": week_b_data,
        "delta_total": delta_total,
        "delta_cases": delta_cases,
        "delta_pct": delta_pct,
    }


def weekly_totals_for_year(reopens_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Aggregate reopen counts by ISO week for a given year."""
    catalog = build_week_catalog(year)
    rows = []

    for item in catalog:
        counts = count_reopens_in_week(reopens_df, year, item["week"])
        rows.append(
            {
                "week": item["week"],
                "label": item["label"],
                "start": item["start"],
                "end": item["end"],
                "total": counts["total"],
                "unique_cases": counts["unique_cases"],
            }
        )

    return pd.DataFrame(rows)


def build_weekly_comparison_donut(comparison: dict) -> go.Figure:
    """Donut chart comparing reopen totals between two ISO weeks."""
    week_a = comparison["week_a"]
    week_b = comparison["week_b"]
    values = [week_a["total"], week_b["total"]]
    labels = [week_a["short_label"], week_b["short_label"]]
    total = sum(values)

    if total == 0:
        pie_values = [1, 1]
        hover_text = [
            f"{week_a['short_label']}<br>{week_a['label']}<br>Reopens: 0",
            f"{week_b['short_label']}<br>{week_b['label']}<br>Reopens: 0",
        ]
        colors = ["#1e3a5f", "#3b2f5c"]
    else:
        pie_values = values
        hover_text = [
            (
                f"{week_a['short_label']}<br>{week_a['label']}<br>"
                f"Reopens: {week_a['total']}<br>"
                f"Casos únicos: {week_a['unique_cases']}"
            ),
            (
                f"{week_b['short_label']}<br>{week_b['label']}<br>"
                f"Reopens: {week_b['total']}<br>"
                f"Casos únicos: {week_b['unique_cases']}"
            ),
        ]
        colors = [THEME_PRIMARY, THEME_SECONDARY]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=pie_values,
                hole=0.62,
                marker=dict(
                    colors=colors,
                    line=dict(color="#0a0a0a", width=2),
                ),
                textinfo="none",
                hoverinfo="text",
                hovertext=hover_text,
                sort=False,
            )
        ]
    )

    layout = dark_chart_layout(None, height=400)
    layout["margin"] = dict(l=24, r=24, t=24, b=72)
    fig.update_layout(**layout, showlegend=True)

    center_text = f"<b>{total}</b><br><span style='font-size:12px;color:#94a3b8'>reopens</span>"
    fig.add_annotation(
        text=center_text,
        x=0.5,
        y=0.5,
        font=dict(size=22, color=THEME_TEXT),
        showarrow=False,
    )

    return fig


def format_delta_pct(delta_pct: float | None) -> str:
    """Format percentage delta for display."""
    if delta_pct is None:
        return "Sin variación (base en 0)"
    direction = "+" if delta_pct >= 0 else ""
    return f"{direction}{delta_pct:.1f}% vs Semana A"
