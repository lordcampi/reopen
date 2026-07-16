"""Shared Plotly styling for dark dashboard charts."""

THEME_PRIMARY = "#3b82f6"
THEME_SECONDARY = "#8b5cf6"
THEME_ACCENT = "#06b6d4"
THEME_MUTED = "#64748b"
THEME_TEXT = "#f1f5f9"
THEME_TEXT_MUTED = "#94a3b8"
DONUT_COLORS = [
    "#3b82f6",
    "#8b5cf6",
    "#06b6d4",
    "#f59e0b",
    "#10b981",
    "#ec4899",
    "#6366f1",
    "#14b8a6",
]


def dark_chart_layout(title: str | None = None, height: int = 420) -> dict:
    """Base layout for dark-theme Plotly charts."""
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=THEME_TEXT),
        margin=dict(l=24, r=24, t=48 if title else 24, b=80),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=THEME_TEXT_MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(size=16, color=THEME_TEXT),
            x=0.5,
            xanchor="center",
        )
    return layout
