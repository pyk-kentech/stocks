from __future__ import annotations

from pathlib import Path
from typing import Any

from stock_risk_mcp.adapters.file_utils import load_records


def load_import_records(path: str | Path, required_columns: set[str]) -> list[dict[str, Any]]:
    file_path = Path(path)
    if file_path.suffix.lower() not in {".csv", ".json"}:
        raise ValueError(f"Unsupported import file extension for {file_path}. Use .csv or .json.")
    records = load_records(file_path)
    columns = set().union(*(record.keys() for record in records)) if records else set()
    missing = required_columns - columns
    if missing:
        raise ValueError(f"Import file is missing required columns: {', '.join(sorted(missing))}")
    return records
