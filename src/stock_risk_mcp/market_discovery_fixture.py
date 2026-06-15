from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from stock_risk_mcp.market_discovery_models import (
    MarketDiscoveryConfig,
    MarketDiscoveryFixture,
)


CSV_FIELDS = [
    "schema_version", "as_of_timestamp", "min_price", "max_price",
    "min_price_change_pct", "min_volume_spike_ratio",
    "min_dollar_volume_spike_ratio", "min_average_dollar_volume_20d",
    "max_candidates", "ticker", "observed_at", "price", "previous_close",
    "volume", "average_volume_20d", "average_dollar_volume_20d",
]
CONFIG_FIELDS = CSV_FIELDS[2:9]
ROW_FIELDS = CSV_FIELDS[9:]
DATETIME_ADAPTER = TypeAdapter(datetime)


def load_market_discovery_fixture(path: str | Path) -> tuple[MarketDiscoveryFixture, str]:
    path = Path(path)
    try:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return MarketDiscoveryFixture.model_validate(json.loads(path.read_text(encoding="utf-8"))), "JSON"
        if suffix == ".csv":
            return _load_csv(path), "CSV"
        raise ValueError("fixture extension must be .json or .csv")
    except Exception as exc:
        raise ValueError(f"invalid market discovery fixture: {exc}") from exc


def _load_csv(path: Path) -> MarketDiscoveryFixture:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != CSV_FIELDS:
            raise ValueError("CSV header must exactly match the v3.3 schema")
        records = list(reader)
    if not records:
        raise ValueError("CSV must contain at least one row")

    configs = []
    for record in records:
        values = {field: record[field] for field in CONFIG_FIELDS}
        values["max_price"] = values["max_price"] or None
        configs.append(MarketDiscoveryConfig.model_validate(values))
    first_config = configs[0]
    if any(item != first_config for item in configs[1:]):
        raise ValueError("CSV scanner config must be identical across rows")
    if any(record["schema_version"] != records[0]["schema_version"] for record in records):
        raise ValueError("CSV schema_version must be identical across rows")
    as_of_timestamps = [DATETIME_ADAPTER.validate_python(record["as_of_timestamp"]) for record in records]
    if any(value.tzinfo is None or value.utcoffset() is None for value in as_of_timestamps):
        raise ValueError("CSV as_of_timestamp must include timezone")
    if any(value != as_of_timestamps[0] for value in as_of_timestamps[1:]):
        raise ValueError("CSV as_of_timestamp must be identical across rows")

    return MarketDiscoveryFixture.model_validate({
        "schema_version": records[0]["schema_version"],
        "as_of_timestamp": records[0]["as_of_timestamp"],
        "scanner_config": first_config.model_dump(),
        "rows": [{field: record[field] for field in ROW_FIELDS} for record in records],
    })
