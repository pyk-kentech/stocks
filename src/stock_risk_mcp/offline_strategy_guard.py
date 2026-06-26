from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput, OfflineStrategyReadinessStatus


def validate_offline_strategy_input_gate(pipeline_input: OfflineStrategyPipelineInput) -> tuple[OfflineStrategyReadinessStatus, list[str], list[str]]:
    findings: list[str] = []
    gaps: list[str] = []
    if pipeline_input.manifest is None and not pipeline_input.ohlcv_rows:
        gaps.append("MISSING_DATASET_INPUT")
    if pipeline_input.primary_walk_forward_mode.value not in {
        "ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        "ROLLING_CHRONOLOGICAL_WALK_FORWARD",
    }:
        gaps.append("NON_CHRONOLOGICAL_SPLIT")
        return OfflineStrategyReadinessStatus.BLOCKED_NON_CHRONOLOGICAL_SPLIT, findings, gaps
    if pipeline_input.primary_walk_forward_mode.value == "ROLLING_CHRONOLOGICAL_WALK_FORWARD":
        findings.append("ROLLING_MODE_IS_SECONDARY_EVIDENCE_ONLY")
    if not pipeline_input.ohlcv_rows and pipeline_input.manifest and pipeline_input.manifest.row_count <= 0:
        gaps.append("MANIFEST_ROW_COUNT_GAP")
        return OfflineStrategyReadinessStatus.DATA_GAP, findings, gaps
    return OfflineStrategyReadinessStatus.DATASET_COMPATIBILITY_READY, findings, gaps
