"""Weekly aggregation and comparison for reopen analytics."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

THEME_PRIMARY = "#2563eb"
THEME_SECONDARY = "#7c3aed"
THEME_ACCENT = "#0ea5e9"
THEME_MUTED = "#94a3b8"
THEME_HIGHLIGHT = "#f59e0b"


def _format_short_date(value: date) -> str:
    return f"{value.day} {MONTHS_ES[value.month]}"


def format_week_label(year: int, week: int, start: date, end: date) -> str:
    """Build a human-readable label for an ISO week."""
    return (
        f"Semana {week} ({_format_short_date(start)} – "
        f"{_format_short_date(end)} {end.year})"
    )


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


def _chart_layout(title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=18, color="#0f172a")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#334155"),
        margin=dict(l=40, r=24, t=64, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(showgrid=False, linecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0", zeroline=False),
    )


def build_comparison_chart(comparison: dict) -> go.Figure:
    """Grouped bar chart comparing two ISO weeks."""
    week_a = comparison["week_a"]
    week_b = comparison["week_b"]
    metrics = ["Reopens totales", "Casos únicos"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=week_a["label"],
            x=metrics,
            y=[week_a["total"], week_a["unique_cases"]],
            marker=dict(color=THEME_PRIMARY, line=dict(width=0)),
            text=[week_a["total"], week_a["unique_cases"]],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name=week_b["label"],
            x=metrics,
            y=[week_b["total"], week_b["unique_cases"]],
            marker=dict(color=THEME_SECONDARY, line=dict(width=0)),
            text=[week_b["total"], week_b["unique_cases"]],
            textposition="outside",
        )
    )

    fig.update_layout(
        **_chart_layout("Comparación semanal"),
        barmode="group",
        bargap=0.28,
        bargroupgap=0.12,
        height=420,
    )

    delta_pct = comparison["delta_pct"]
    if delta_pct is not None:
        direction = "↑" if delta_pct >= 0 else "↓"
        annotation = f"{direction} {abs(delta_pct):.1f}% en reopens totales"
    else:
        annotation = "Sin variación porcentual (base en 0)"

    fig.add_annotation(
        text=annotation,
        xref="paper",
        yref="paper",
        x=0,
        y=1.12,
        showarrow=False,
        font=dict(size=13, color="#64748b"),
    )

    return fig


def build_trend_chart(
    weekly_df: pd.DataFrame, week_a: int, week_b: int
) -> go.Figure:
    """Weekly trend chart for the full year with selected weeks highlighted."""
    colors = [
        THEME_HIGHLIGHT if week in (week_a, week_b) else THEME_ACCENT
        for week in weekly_df["week"]
    ]

    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(
        go.Bar(
            x=weekly_df["week"],
            y=weekly_df["total"],
            name="Reopens",
            marker=dict(color=colors, line=dict(width=0)),
            hovertext=weekly_df["label"],
            hoverinfo="text+y",
        )
    )

    fig.update_layout(
        **_chart_layout("Tendencia semanal del año"),
        height=380,
        xaxis_title="Semana ISO",
        yaxis_title="Reopens",
        showlegend=False,
    )

    for week in (week_a, week_b):
        row = weekly_df.loc[weekly_df["week"] == week]
        if row.empty:
            continue
        total = int(row.iloc[0]["total"])
        fig.add_vline(
            x=week,
            line_width=1.5,
            line_dash="dot",
            line_color=THEME_HIGHLIGHT if week == week_a else THEME_SECONDARY,
        )
        fig.add_annotation(
            x=week,
            y=total,
            text=f"S{week}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-28,
            font=dict(size=11, color="#475569"),
        )

    return fig
