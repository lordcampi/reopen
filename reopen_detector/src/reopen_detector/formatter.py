"""Format detection results for display."""

import pandas as pd

from reopen_detector.config import VISIBLE_COLUMNS_MAP


def format_visible_table(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare the visible table from technical detection results.

    Args:
        df: DataFrame from detect_reopens with technical columns.

    Returns:
        DataFrame with visible columns: Número de caso, Fecha, Agente.
    """
    if df.empty:
        return pd.DataFrame(columns=list(VISIBLE_COLUMNS_MAP.values()))

    visible = pd.DataFrame()

    for src_col, dest_col in VISIBLE_COLUMNS_MAP.items():
        if src_col in df.columns:
            visible[dest_col] = df[src_col]

    # Format date column for display
    if "Fecha" in visible.columns:
        visible["Fecha"] = visible["Fecha"].apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else ""
        )

    return visible


def format_date_for_display(dt) -> str:
    """Format a datetime for human-readable display."""
    if pd.isna(dt) or dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")