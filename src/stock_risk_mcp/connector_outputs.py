from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_csv_output(path: str | Path, records: list[dict[str, Any]]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0]) if records else []
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return output_path


def count_output_rows(path: str | Path) -> int:
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as file:
            return sum(1 for _ in csv.DictReader(file))
    if file_path.suffix.lower() == ".json":
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            data = data["records"]
        elif isinstance(data, dict):
            data = list(data.values())
        if not isinstance(data, list):
            raise ValueError(f"JSON connector output must contain a list: {file_path}")
        return len(data)
    raise ValueError(f"Unsupported connector output extension: {file_path}")
