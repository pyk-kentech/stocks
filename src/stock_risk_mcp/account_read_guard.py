from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.account_read_models import (
    AccountReadGapEntry,
    AccountReadPipelineInput,
    AccountReadReadinessStatus,
)


_BLOCKED_MARKERS = (
    "authorization",
    "bearer ",
    "api_key",
    "secret",
    "token",
    "password",
    "account_number",
    "order",
    "mutation",
    "requests",
    "httpx",
    "websocket",
)


def validate_account_read_metadata_safety(metadata: dict[str, object], context: str) -> None:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        lowered_value = str(value).lower()
        if any(marker in lowered_key for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata field: {key}")
        if any(marker in lowered_value for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata value")


def validate_account_read_root(path: str, *, repo_root: Path) -> tuple[bool, str]:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else (repo_root / raw)
    normalized = candidate.resolve()
    safe_root = (repo_root / "local_data" / "account_read").resolve()
    if safe_root == normalized or safe_root in normalized.parents:
        return True, "SAFE_LOCAL_ROOT_ONLY"
    if "/tmp/" in str(normalized) or "/var/folders/" in str(normalized):
        return True, "TEST_TEMP_ONLY"
    return False, "REJECTED_PATH"


def validate_account_read_input_gate(
    pipeline_input: AccountReadPipelineInput,
    *,
    in_pytest: bool = False,
) -> tuple[AccountReadReadinessStatus, list[str], list[AccountReadGapEntry]]:
    findings: list[str] = []
    gaps: list[AccountReadGapEntry] = []

    if pipeline_input.mode.value == "OPT_IN_REAL_READONLY_BOUNDARY":
        findings.append("OPT_IN_BOUNDARY_ONLY")
        if in_pytest:
            gaps.append(
                AccountReadGapEntry(
                    gap_id=f"{pipeline_input.pipeline_id}-PYTEST-NETWORK-BLOCKED",
                    gap_category="BLOCKED_NETWORK_IN_TEST",
                    severity="BLOCKING",
                    message="real account read boundary remains blocked in pytest",
                )
            )
            return AccountReadReadinessStatus.BLOCKED_NETWORK_IN_TEST, findings, gaps
        if not pipeline_input.opt_in.allow_real_account_read:
            gaps.append(
                AccountReadGapEntry(
                    gap_id=f"{pipeline_input.pipeline_id}-OPT-IN-REQUIRED",
                    gap_category="ACCOUNT_READ_OPT_IN_REQUIRED",
                    severity="BLOCKING",
                    message="real account read requires explicit opt-in",
                )
            )
            return AccountReadReadinessStatus.ACCOUNT_READ_OPT_IN_REQUIRED, findings, gaps

    if pipeline_input.snapshot_fixture is None and pipeline_input.mode.value != "OPT_IN_REAL_READONLY_BOUNDARY":
        gaps.append(
            AccountReadGapEntry(
                gap_id=f"{pipeline_input.pipeline_id}-MISSING-SNAPSHOT",
                gap_category="DATA_GAP",
                severity="BLOCKING",
                message="manual or mocked account snapshot fixture is required",
            )
        )
        return AccountReadReadinessStatus.DATA_GAP, findings, gaps

    for audit in pipeline_input.audit_records:
        validate_account_read_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="account read audit",
        )

    return AccountReadReadinessStatus.ACCOUNT_READ_READY, findings, gaps
