"""Export results to CSV and Excel formats."""

from io import BytesIO

import pandas as pd


def export_to_csv(visible_df: pd.DataFrame, technical_df: pd.DataFrame = None) -> bytes:
    """Export results as CSV.

    Args:
        visible_df: Formatted visible table.
        technical_df: Optional technical detail DataFrame.

    Returns:
        CSV content as bytes.
    """
    # If technical details are provided, include them
    if technical_df is not None and not technical_df.empty:
        export_df = technical_df.copy()
    else:
        export_df = visible_df.copy()

    return export_df.to_csv(index=False).encode("utf-8-sig")


def export_to_excel(visible_df: pd.DataFrame, technical_df: pd.DataFrame) -> bytes:
    """Export results as Excel with two sheets.

    Sheet 1: resultado_visible (visible columns)
    Sheet 2: detalle_tecnico (all technical columns)

    Args:
        visible_df: Formatted visible table.
        technical_df: Technical detail DataFrame.

    Returns:
        Excel file content as bytes.
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        visible_df.to_excel(writer, sheet_name="resultado_visible", index=False)

        if technical_df is not None and not technical_df.empty:
            technical_df.to_excel(writer, sheet_name="detalle_tecnico", index=False)

    output.seek(0)
    return output.getvalue()