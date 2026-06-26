from __future__ import annotations

from stock_risk_mcp.historical_market_data_models import HistoricalOhlcvRow
from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyDatasetCompatibilityReport,
    OfflineStrategyPipelineInput,
    OfflineStrategyReadinessStatus,
    OfflineStrategySupportStatus,
)


def resolve_offline_strategy_rows(pipeline_input: OfflineStrategyPipelineInput) -> list[HistoricalOhlcvRow]:
    return list(pipeline_input.ohlcv_rows)


def build_offline_strategy_dataset_compatibility(pipeline_input: OfflineStrategyPipelineInput, rows: list[HistoricalOhlcvRow]) -> OfflineStrategyDatasetCompatibilityReport:
    findings: list[str] = []
    readiness = OfflineStrategyReadinessStatus.DATASET_COMPATIBILITY_READY
    support = OfflineStrategySupportStatus.SUPPORTED
    if not rows and pipeline_input.manifest is not None:
        findings.append("MANIFEST_ONLY_MODE")
    if not rows and (pipeline_input.manifest is None or pipeline_input.manifest.row_count <= 0):
        readiness = OfflineStrategyReadinessStatus.DATA_GAP
        support = OfflineStrategySupportStatus.BLOCKED
        findings.append("ROW_COVERAGE_GAP")
    if rows and any(row.high_price is None or row.low_price is None for row in rows):
        findings.append("HIGH_LOW_PARTIAL_GAP")
        support = OfflineStrategySupportStatus.PARTIAL
    return OfflineStrategyDatasetCompatibilityReport(
        report_id=f"{pipeline_input.dataset_id}-DATASET-COMPATIBILITY-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        support_status=support,
        findings=findings,
        row_count=len(rows) if rows else (pipeline_input.manifest.row_count if pipeline_input.manifest else 0),
    )
