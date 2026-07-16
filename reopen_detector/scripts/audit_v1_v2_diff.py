#!/usr/bin/env python3
"""Compare V1 vs V2 reopen detection per case for a date range.

Usage:
    python scripts/audit_v1_v2_diff.py path/to/file.csv --start 2026-07-06 --end 2026-07-12

Prints summary metrics and a per-case diff table to stdout.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reopen_detector.detector import detect_reopens
from reopen_detector.detector_v2 import detect_reopens_v2
from reopen_detector.filters import filter_by_reopen_date
from reopen_detector.loader import load_csv
from reopen_detector.normalizer import normalize_dataframe


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _count_by_case(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("case_number").size()


def audit(
    csv_path: Path,
    start_date: date,
    end_date: date,
    start_time: time = time(0, 0),
    end_time: time = time(23, 59, 59),
) -> pd.DataFrame:
    raw_df = load_csv(csv_path)
    normalized_df, _ = normalize_dataframe(raw_df)

    v1 = filter_by_reopen_date(
        detect_reopens(
            normalized_df,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
        ),
        start_date,
        end_date,
        start_time,
        end_time,
    )
    v2 = filter_by_reopen_date(
        detect_reopens_v2(
            normalized_df,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
        ),
        start_date,
        end_date,
        start_time,
        end_time,
    )

    counts_v1 = _count_by_case(v1).rename("v1_count")
    counts_v2 = _count_by_case(v2).rename("v2_count")
    diff = pd.concat([counts_v1, counts_v2], axis=1).fillna(0).astype(int)
    diff["delta"] = diff["v2_count"] - diff["v1_count"]
    diff = diff.reset_index().sort_values(
        by=["delta", "v2_count", "case_number"],
        ascending=[False, False, True],
    )

    print("=== Resumen ===")
    print(f"Rango: {start_date} a {end_date}")
    print(f"V1 — reopens: {len(v1)}, casos: {v1['case_number'].nunique() if not v1.empty else 0}")
    print(f"V2 — reopens: {len(v2)}, casos: {v2['case_number'].nunique() if not v2.empty else 0}")

    only_v1 = diff[(diff["v1_count"] > 0) & (diff["v2_count"] == 0)]
    only_v2 = diff[(diff["v2_count"] > 0) & (diff["v1_count"] == 0)]
    v2_more = diff[diff["delta"] > 0]

    print(f"Solo V1: {len(only_v1)} casos")
    print(f"Solo V2: {len(only_v2)} casos")
    print(f"V2 > V1: {len(v2_more)} casos")
    print()
    print("=== Diff por caso (top 30 por delta) ===")
    print(diff.head(30).to_string(index=False))

    return diff


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auditoría V1 vs V2 por caso en un rango de fechas."
    )
    parser.add_argument("csv_path", type=Path, help="Ruta al archivo CSV")
    parser.add_argument("--start", required=True, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Fecha fin YYYY-MM-DD")
    args = parser.parse_args()

    audit(
        csv_path=args.csv_path,
        start_date=_parse_date(args.start),
        end_date=_parse_date(args.end),
    )


if __name__ == "__main__":
    main()
