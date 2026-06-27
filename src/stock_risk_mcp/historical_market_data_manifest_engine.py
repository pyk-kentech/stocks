from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.historical_market_data_models import (
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataStorageCapabilityReport,
    HistoricalMarketDataStorageCapabilityRow,
    HistoricalMarketDataStorageFormat,
    HistoricalOhlcvDatasetManifest,
    HistoricalOhlcvRow,
    to_feature_store_price_bar,
)


def build_historical_market_data_storage_capability_report(
    dataset_id: str,
    requested_storage_formats: list[HistoricalMarketDataStorageFormat],
) -> HistoricalMarketDataStorageCapabilityReport:
    rows: list[HistoricalMarketDataStorageCapabilityRow] = []
    for item in requested_storage_formats:
        if item in {HistoricalMarketDataStorageFormat.IN_MEMORY, HistoricalMarketDataStorageFormat.JSON, HistoricalMarketDataStorageFormat.JSONL}:
            rows.append(
                HistoricalMarketDataStorageCapabilityRow(
                    storage_format=item,
                    supported=True,
                    status=HistoricalMarketDataReadinessStatus.COVERAGE_READY,
                    notes=["built-in local backend"],
                )
            )
            continue
        module_name = "duckdb" if item == HistoricalMarketDataStorageFormat.DUCKDB else "polars"
        supported = importlib.util.find_spec(module_name) is not None
        rows.append(
            HistoricalMarketDataStorageCapabilityRow(
                storage_format=item,
                supported=supported,
                status=HistoricalMarketDataReadinessStatus.COVERAGE_READY if supported else HistoricalMarketDataReadinessStatus.DATA_GAP,
                notes=["optional dependency detected" if supported else f"optional dependency missing: {module_name}"],
            )
        )
    return HistoricalMarketDataStorageCapabilityReport(report_id=f"{dataset_id}-STORAGE-CAPABILITY-REPORT", rows=rows)


def build_historical_ohlcv_dataset_manifest(
    pipeline_input: HistoricalMarketDataPipelineInput,
    ohlcv_rows: list[HistoricalOhlcvRow],
) -> tuple[HistoricalOhlcvDatasetManifest, list]:
    root = validate_safe_local_root(pipeline_input.store_root)
    root.mkdir(parents=True, exist_ok=True)
    storage_refs = sorted({row.source_ref for row in ohlcv_rows})
    dataset_dir = root / pipeline_input.dataset_id.lower()
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rows_path = dataset_dir / "ohlcv_rows.json"
    manifest_path = dataset_dir / "historical_ohlcv_dataset_manifest.json"
    rows_path.write_text(json.dumps([row.model_dump(mode="json") for row in ohlcv_rows], indent=2), encoding="utf-8")
    manifest = HistoricalOhlcvDatasetManifest(
        manifest_id=f"{pipeline_input.dataset_id}-NORMALIZED-MANIFEST",
        dataset_id=pipeline_input.dataset_id,
        store_root=str(root),
        manifest_path=str(manifest_path),
        ohlcv_rows_path=str(rows_path),
        partition_spec=pipeline_input.partition_spec,
        row_count=len(ohlcv_rows),
        intervals=sorted({row.interval.value for row in ohlcv_rows}),
        instrument_ids=sorted({row.instrument_id for row in ohlcv_rows}),
        storage_format=HistoricalMarketDataStorageFormat.JSON,
        storage_refs=storage_refs,
        readiness_status=HistoricalMarketDataReadinessStatus.V10_MANIFEST_READY if ohlcv_rows else HistoricalMarketDataReadinessStatus.DATA_GAP,
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest, [to_feature_store_price_bar(row) for row in ohlcv_rows]


def load_historical_ohlcv_dataset_manifest(path: str | Path) -> HistoricalOhlcvDatasetManifest:
    return HistoricalOhlcvDatasetManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_historical_ohlcv_rows_from_manifest(manifest: HistoricalOhlcvDatasetManifest) -> list[HistoricalOhlcvRow]:
    if not manifest.ohlcv_rows_path:
        return []
    payload = json.loads(Path(manifest.ohlcv_rows_path).read_text(encoding="utf-8"))
    return [HistoricalOhlcvRow.model_validate(item) for item in payload]
