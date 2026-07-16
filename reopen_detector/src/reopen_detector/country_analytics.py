"""Country-level reopen aggregation and charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from reopen_detector.chart_theme import DONUT_COLORS, THEME_TEXT, dark_chart_layout

EMPTY_COUNTRY_LABEL = "Sin país"


def aggregate_reopens_by_country(reopens_df: pd.DataFrame) -> pd.DataFrame:
    """Count reopens per country, sorted descending."""
    if reopens_df.empty or "country" not in reopens_df.columns:
        return pd.DataFrame(columns=["country", "total"])

    df = reopens_df.copy()
    df["country"] = df["country"].fillna("").astype(str).str.strip()
    df.loc[df["country"] == "", "country"] = EMPTY_COUNTRY_LABEL

    grouped = (
        df.groupby("country", as_index=False)
        .size()
        .rename(columns={"size": "total"})
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    return grouped


def build_country_donut_chart(reopens_df: pd.DataFrame) -> go.Figure | None:
    """Build a donut chart of reopens by country for the selected range."""
    grouped = aggregate_reopens_by_country(reopens_df)
    if grouped.empty:
        return None

    labels = grouped["country"].tolist()
    values = grouped["total"].tolist()
    total = sum(values)

    hover_text = [
        f"{label}<br>Reopens: {value}<br>{(value / total * 100):.1f}%"
        for label, value in zip(labels, values)
    ]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=DONUT_COLORS[: len(labels)], line=dict(color="#0a0a0a", width=2)),
                textinfo="none",
                hoverinfo="text",
                hovertext=hover_text,
                sort=False,
            )
        ]
    )

    fig.update_layout(
        **dark_chart_layout("Reopens por país", height=440),
        showlegend=True,
    )
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:12px;color:#94a3b8'>reopens</span>",
        x=0.5,
        y=0.5,
        font=dict(size=22, color=THEME_TEXT),
        showarrow=False,
    )

    return fig
