from __future__ import annotations

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionAuditRecord,
    ControlledExecutionMode,
)


def build_controlled_execution_audit_record(
    *,
    pipeline_id: str,
    action_type: str,
    created_at,
    mode: ControlledExecutionMode,
    decision: str,
    source_refs: list[str] | None = None,
    order_draft_hash: str | None = None,
    approval_ref_hash: str | None = None,
    idempotency_key: str | None = None,
    reason_codes: list[str] | None = None,
) -> ControlledExecutionAuditRecord:
    return ControlledExecutionAuditRecord(
        audit_id=f"{pipeline_id}-{action_type}-AUDIT",
        action_type=action_type,
        created_at=created_at,
        source_refs=source_refs or [],
        order_draft_hash=order_draft_hash,
        approval_ref_hash=approval_ref_hash,
        idempotency_key=idempotency_key,
        mode=mode,
        decision=decision,
        reason_codes=reason_codes or [],
    )
