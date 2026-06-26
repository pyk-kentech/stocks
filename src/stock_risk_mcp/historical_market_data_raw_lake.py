from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartRawLakeRecord,
    HistoricalChartRawResponse,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataStorageFormat,
)


def persist_historical_chart_raw_lake(
    pipeline_input: HistoricalMarketDataPipelineInput,
    raw_responses: list[HistoricalChartRawResponse],
) -> list[HistoricalChartRawLakeRecord]:
    root = validate_safe_local_root(pipeline_input.raw_lake_root)
    root.mkdir(parents=True, exist_ok=True)
    records: list[HistoricalChartRawLakeRecord] = []
    persisted_at = datetime.now().astimezone()
    for response in raw_responses:
        filename = f"{response.response_id.lower()}.json"
        path = root / filename
        payload = response.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        records.append(
            HistoricalChartRawLakeRecord(
                record_id=f"{response.response_id}-RAW-LAKE",
                response_id=response.response_id,
                dataset_id=pipeline_input.dataset_id,
                relative_path=filename,
                storage_format=HistoricalMarketDataStorageFormat.JSON,
                source_kind=response.source_kind,
                redacted=True,
                persisted_at=persisted_at,
            )
        )
    return records
