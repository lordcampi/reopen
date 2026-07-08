"""CSV structure validation."""

import pandas as pd

from reopen_detector.config import REQUIRED_COLUMNS


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Validate that the DataFrame has the required structure.

    Args:
        df: DataFrame loaded from CSV.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if df is None or df.empty:
        errors.append("El archivo CSV está vacío o no contiene datos.")
        return errors

    missing_columns = [
        col for col in REQUIRED_COLUMNS if col not in df.columns
    ]

    if missing_columns:
        errors.append(
            f"Faltan las siguientes columnas obligatorias: {', '.join(missing_columns)}"
        )

    return errors