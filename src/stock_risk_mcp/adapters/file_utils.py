from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_records(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    if file_path.suffix.lower() == ".json":
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            if isinstance(data.get("records"), list):
                data = data["records"]
            else:
                data = list(data.values())
        if not isinstance(data, list):
            raise ValueError(f"JSON data file must contain a list or mapping of records: {file_path}")
        return [_coerce_record(record, file_path) for record in data]

    if file_path.suffix.lower() == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as file:
            return [dict(row) for row in csv.DictReader(file)]

    raise ValueError(f"Unsupported data file extension for {file_path}. Use .json or .csv.")


def find_record_by_ticker(records: list[dict[str, Any]], ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
    for record in records:
        if str(record.get("ticker", "")).upper() == symbol:
            return _normalize_empty_strings(record)
    raise LookupError(f"No record found for ticker {symbol}")


def _coerce_record(record: Any, file_path: Path) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"Every record in {file_path} must be an object")
    return record


def _normalize_empty_strings(record: dict[str, Any]) -> dict[str, Any]:
    return {key: (None if value == "" else value) for key, value in record.items()}
