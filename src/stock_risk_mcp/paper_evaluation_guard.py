from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.feature_store_models import FeatureStoreReadinessStatus
from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationGapEntry,
    PaperEvaluationPipelineInput,
    PaperEvaluationReadinessStatus,
)


_BLOCKED_MARKERS = (
    "authorization",
    "bearer ",
    "api_key",
    "secret",
    "token",
    "password",
    "account",
    "order",
    "broker",
    "kiwoom",
    "ls",
    "websocket",
    "requests",
    "httpx",
    "shell",
)


def validate_paper_evaluation_metadata_safety(metadata: dict[str, object], context: str) -> None:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        lowered_value = str(value).lower()
        if any(marker in lowered_key for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata field: {key}")
        if any(marker in lowered_value for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata value")


def validate_paper_evaluation_root(path: str, *, repo_root: Path) -> tuple[bool, str]:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else (repo_root / raw)
    normalized = candidate.resolve()
    safe_root = (repo_root / "local_data" / "paper_evaluation").resolve()
    if safe_root == normalized or safe_root in normalized.parents:
        return True, "SAFE_LOCAL_ROOT_ONLY"
    if "/tmp/" in str(normalized) or "/var/folders/" in str(normalized):
        return True, "TEST_TEMP_ONLY"
    return False, "REJECTED_PATH"


def validate_paper_evaluation_input_gate(
    pipeline_input: PaperEvaluationPipelineInput,
) -> tuple[PaperEvaluationReadinessStatus, list[str], list[PaperEvaluationGapEntry]]:
    findings: list[str] = []
    gaps: list[PaperEvaluationGapEntry] = []

    if pipeline_input.training_dataset_manifest.readiness_status == FeatureStoreReadinessStatus.BLOCKED_LEAKAGE:
        findings.append("LEAKAGE_BLOCKED")
        gaps.append(
            PaperEvaluationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-LEAKAGE-BLOCKED",
                gap_category="LEAKAGE_BLOCKED",
                severity="BLOCKING",
                message="v10 leakage report blocks paper evaluation",
            )
        )
        return PaperEvaluationReadinessStatus.LEAKAGE_BLOCKED, findings, gaps

    if pipeline_input.leakage_report.readiness_status == FeatureStoreReadinessStatus.BLOCKED_LEAKAGE:
        findings.append("LEAKAGE_BLOCKED")
        gaps.append(
            PaperEvaluationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-LEAKAGE-REPORT-BLOCKED",
                gap_category="LEAKAGE_BLOCKED",
                severity="BLOCKING",
                message="v10 leakage report readiness is BLOCKED_LEAKAGE",
            )
        )
        return PaperEvaluationReadinessStatus.LEAKAGE_BLOCKED, findings, gaps

    if pipeline_input.training_dataset_manifest.dataset_profile.value == "FULL_INTRADAY_PROFILE":
        findings.append("REJECTED")
        gaps.append(
            PaperEvaluationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-FULL-INTRADAY-BLOCKED",
                gap_category="REJECTED",
                severity="BLOCKING",
                message="FULL_INTRADAY_PROFILE remains blocked by default",
            )
        )
        return PaperEvaluationReadinessStatus.REJECTED, findings, gaps

    if not pipeline_input.feature_rows or not pipeline_input.training_rows:
        findings.append("DATA_GAP")
        gaps.append(
            PaperEvaluationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-MISSING-ROWS",
                gap_category="DATA_GAP",
                severity="BLOCKING",
                message="feature rows and training rows are required",
            )
        )
        return PaperEvaluationReadinessStatus.DATA_GAP, findings, gaps

    if not pipeline_input.walk_forward_plan.splits:
        findings.append("DATA_SNOOPING_GAP")
        gaps.append(
            PaperEvaluationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-MISSING-SPLITS",
                gap_category="DATA_SNOOPING_GAP",
                severity="BLOCKING",
                message="walk-forward split plan is required",
            )
        )
        return PaperEvaluationReadinessStatus.DATA_SNOOPING_GAP, findings, gaps

    for audit in pipeline_input.audit_records:
        validate_paper_evaluation_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="paper evaluation audit",
        )

    return PaperEvaluationReadinessStatus.PLAN_READY, findings, gaps


def ensure_signal_does_not_use_labels(feature_values: dict[str, object]) -> None:
    for key in feature_values:
        lowered = key.lower()
        if lowered in {"forward_return", "future_return", "mfe", "mae", "target", "label", "outcome"}:
            raise ValueError(f"label-derived signal field blocked: {key}")
