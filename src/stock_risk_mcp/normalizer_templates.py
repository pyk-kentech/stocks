from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from stock_risk_mcp.adapters.file_utils import load_records
from stock_risk_mcp.normalize_run import NormalizeSourceResult, NormalizerType


def start_normalization(name: str, normalizer_type: NormalizerType, input_path: str | Path):
    result = NormalizeSourceResult(
        normalizer_name=name, normalizer_type=normalizer_type, input_path=str(input_path),
    )
    try:
        records = load_records(input_path)
        result.row_count = len(records)
        return result, records
    except Exception as error:
        result.error_count = 1
        result.errors.append(str(error))
        return result, None


def mapped(record: dict[str, Any], columns: dict[str, str], key: str, required: bool = False):
    source = columns.get(key, key)
    value = record.get(source)
    if required and value in (None, ""):
        raise ValueError(f"missing required value: {key}")
    return value


def parse_date(value: Any) -> date:
    return date.fromisoformat(str(value).strip()[:10])


def after_cutoff(value: Any, as_of_date: date | None) -> bool:
    return bool(as_of_date and parse_date(value) > as_of_date)


def row_error(result: NormalizeSourceResult, index: int, error: Exception) -> None:
    result.error_count += 1
    result.errors.append(f"row {index}: {error}")


def write_normalized_output(
    result: NormalizeSourceResult,
    records: list[dict[str, Any]],
    output_dir: str | Path,
    output_name: str | None,
) -> NormalizeSourceResult:
    if not records:
        return result
    name = output_name or f"{Path(result.input_path).stem}_{result.normalizer_name}.csv"
    if Path(name).name != name or Path(name).suffix.lower() not in {".csv", ".json"}:
        result.error_count += 1
        result.errors.append("output_name must be a safe .csv or .json file name")
        return result
    output = Path(output_dir) / name
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        with output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    result.output_path = str(output)
    result.normalized_count = len(records)
    return result


def text(value: Any, default: str = "") -> str:
    return str(value).strip() if value not in (None, "") else default


def upper(value: Any, default: str = "") -> str:
    return text(value, default).upper()
