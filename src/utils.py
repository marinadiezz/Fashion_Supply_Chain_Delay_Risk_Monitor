from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


DATE_COLUMNS = {
    "collections": ["launch_date"],
    "purchase_orders": [
        "planned_order_date",
        "actual_order_date",
        "planned_ship_date",
        "actual_ship_date",
        "planned_arrival_date",
        "actual_arrival_date",
    ],
    "milestones": ["planned_date", "actual_date"],
    "risks": ["date_identified", "target_resolution_date"],
    "incidents": ["date_opened", "date_closed"],
    "actions": ["due_date", "completion_date"],
}


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator in (0, None) or pd.isna(denominator):
        return default
    return numerator / denominator


def pct(value: float, decimals: int = 1) -> str:
    if pd.isna(value):
        return "0.0%"
    return f"{value * 100:.{decimals}f}%"


def parse_dates(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def load_csv(name: str, processed: bool = True) -> pd.DataFrame:
    base = PROCESSED_DIR if processed else RAW_DIR
    path = base / f"{name}.csv"
    df = pd.read_csv(path)
    return parse_dates(df, DATE_COLUMNS.get(name, []))


def load_all(processed: bool = True) -> dict[str, pd.DataFrame]:
    tables = [
        "brands",
        "collections",
        "suppliers",
        "purchase_orders",
        "milestones",
        "risks",
        "incidents",
        "actions",
    ]
    return {table: load_csv(table, processed=processed) for table in tables}


def readiness_band(score: float) -> str:
    if pd.isna(score):
        return "No Data"
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Watch"
    if score >= 50:
        return "At Risk"
    return "Critical"


def days_until(date_value, reference_date: str | pd.Timestamp = "2026-04-25") -> int:
    date_value = pd.to_datetime(date_value)
    reference = pd.to_datetime(reference_date)
    return int((date_value - reference).days)
