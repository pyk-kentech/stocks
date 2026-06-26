from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionGapEntry,
    ControlledExecutionMode,
    ControlledExecutionPipelineInput,
    ControlledExecutionReadinessStatus,
)


_BLOCKED_MARKERS = (
    "authorization",
    "bearer ",
    "api_key",
    "secret",
    "token",
    "password",
    "account_number",
    "broker-submit",
    "http://",
    "https://",
    "requests",
    "httpx",
    "websocket",
)


def validate_controlled_execution_metadata_safety(metadata: dict[str, object], context: str) -> None:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        lowered_value = str(value).lower()
        if any(marker in lowered_key for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata field: {key}")
        if any(marker in lowered_value for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata value")


def validate_controlled_execution_root(path: str, *, repo_root: Path) -> tuple[bool, str]:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else (repo_root / raw)
    normalized = candidate.resolve()
    safe_root = (repo_root / "local_data" / "controlled_execution").resolve()
    if safe_root == normalized or safe_root in normalized.parents:
        return True, "SAFE_LOCAL_ROOT_ONLY"
    if "/tmp/" in str(normalized) or "/var/folders/" in str(normalized):
        return True, "TEST_TEMP_ONLY"
    return False, "REJECTED_PATH"


def validate_controlled_execution_input_gate(
    pipeline_input: ControlledExecutionPipelineInput,
    *,
    in_pytest: bool = False,
) -> tuple[ControlledExecutionReadinessStatus, list[str], list[ControlledExecutionGapEntry]]:
    findings: list[str] = []
    gaps: list[ControlledExecutionGapEntry] = []

    if pipeline_input.mode == ControlledExecutionMode.LIVE_EXECUTION_OPT_IN_BOUNDARY:
        findings.append("LIVE_BOUNDARY_BLOCKED")
        gaps.append(
            ControlledExecutionGapEntry(
                gap_id=f"{pipeline_input.pipeline_id}-LIVE-BOUNDARY-BLOCKED",
                gap_category="LIVE_BOUNDARY_BLOCKED",
                severity="BLOCKING",
                message="live execution boundary remains blocked by default in v13",
            )
        )
        if in_pytest:
            gaps.append(
                ControlledExecutionGapEntry(
                    gap_id=f"{pipeline_input.pipeline_id}-PYTEST-LIVE-BLOCKED",
                    gap_category="BLOCKED_NETWORK_IN_TEST",
                    severity="BLOCKING",
                    message="live boundary is forbidden in pytest",
                )
            )
            return ControlledExecutionReadinessStatus.BLOCKED, findings, gaps

    if in_pytest and pipeline_input.mode not in {
        ControlledExecutionMode.BLOCKED_DEFAULT,
        ControlledExecutionMode.READINESS_REPORT_ONLY,
        ControlledExecutionMode.PREFLIGHT_ONLY,
        ControlledExecutionMode.MOCK_EXECUTION_ONLY,
        ControlledExecutionMode.DRY_RUN_NO_BROKER,
        ControlledExecutionMode.MANUAL_APPROVAL_PACKET_ONLY,
    }:
        gaps.append(
            ControlledExecutionGapEntry(
                gap_id=f"{pipeline_input.pipeline_id}-INVALID-TEST-MODE",
                gap_category="REJECTED_TEST_MODE",
                severity="BLOCKING",
                message="mode is not allowed in pytest",
            )
        )
        return ControlledExecutionReadinessStatus.REJECTED, findings, gaps

    for audit in pipeline_input.audit_records:
        validate_controlled_execution_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="controlled execution audit",
        )
    for record in pipeline_input.prior_audit_records:
        validate_controlled_execution_metadata_safety(
            {
                "action_type": record.action_type,
                "decision": record.decision,
                "source_refs": record.source_refs,
            },
            context="controlled execution prior audit",
        )

    return ControlledExecutionReadinessStatus.READINESS_REPORT_READY, findings, gaps
