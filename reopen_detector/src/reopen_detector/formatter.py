"""Format detection results for display."""

import pandas as pd

from reopen_detector.config import AGGREGATED_COLUMNS_MAP, VISIBLE_COLUMNS_MAP


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


def format_aggregated_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate reopen results: one row per case with a reopen count.

    Groups the filtered reopen events by ``case_number`` and produces
    a single row per case containing:

    - Número de caso
    - Reaperturas en el período (count of reopen events)
    - Última fecha de reapertura
    - Último agente

    Args:
        df: DataFrame from filter_by_reopen_date with columns:
            case_number, reopen_date, agent, ...

    Returns:
        DataFrame with aggregated columns per case.
    """
    if df.empty:
        return pd.DataFrame(columns=list(AGGREGATED_COLUMNS_MAP.values()))

    aggregated = (
        df.groupby("case_number")
        .agg(
            reopen_count=("reopen_date", "count"),
            last_reopen_date=("reopen_date", "max"),
            last_agent=("agent", "last"),
        )
        .reset_index()
    )

    # Rename columns to human-readable names
    aggregated = aggregated.rename(columns=AGGREGATED_COLUMNS_MAP)

    # Reorder columns to match AGGREGATED_COLUMNS_MAP order
    column_order = list(AGGREGATED_COLUMNS_MAP.values())
    aggregated = aggregated[column_order]

    # Format date column
    fecha_col = AGGREGATED_COLUMNS_MAP["last_reopen_date"]
    if fecha_col in aggregated.columns:
        aggregated[fecha_col] = aggregated[fecha_col].apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else ""
        )

    return aggregated


def format_date_for_display(dt) -> str:
    """Format a datetime for human-readable display."""
    if pd.isna(dt) or dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
