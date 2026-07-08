"""CSV file loader with support for multiple separators and encodings."""

import pandas as pd

from reopen_detector.config import CSV_ENCODINGS, CSV_SEPARATORS


def load_csv(file_path_or_buffer) -> pd.DataFrame:
    """Load a CSV file trying different separators and encodings.

    Args:
        file_path_or_buffer: Path to CSV file or file-like object.

    Returns:
        pd.DataFrame with the loaded data.

    Raises:
        ValueError: If the file cannot be parsed with any supported combination.
    """
    # If it's a file-like object (Streamlit UploadedFile), we need to handle it differently
    if hasattr(file_path_or_buffer, "read"):
        content = file_path_or_buffer.read()
        return _load_from_bytes(content)

    return _load_from_path(file_path_or_buffer)


def _load_from_bytes(content: bytes) -> pd.DataFrame:
    """Try to parse CSV content from bytes with different encodings and separators."""
    last_error = None

    for encoding in CSV_ENCODINGS:
        try:
            text = content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue

        for sep in CSV_SEPARATORS:
            try:
                df = pd.read_csv(
                    pd.io.common.StringIO(text),
                    sep=sep,
                    encoding="utf-8",
                    dtype=str,
                )
                # Check if we got a reasonable number of columns
                if len(df.columns) >= 2:
                    return df
            except Exception as e:
                last_error = e
                continue

    raise ValueError(
        f"No se pudo leer el archivo CSV. Último error: {last_error}"
    )


def _load_from_path(path: str) -> pd.DataFrame:
    """Try to parse CSV from a file path with different encodings and separators."""
    last_error = None

    for encoding in CSV_ENCODINGS:
        for sep in CSV_SEPARATORS:
            try:
                df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str)
                if len(df.columns) >= 2:
                    return df
            except Exception as e:
                last_error = e
                continue

    raise ValueError(
        f"No se pudo leer el archivo CSV. Último error: {last_error}"
    )