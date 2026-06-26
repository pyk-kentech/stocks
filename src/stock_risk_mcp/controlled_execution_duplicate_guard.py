from __future__ import annotations

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionDuplicateGuardState,
    ControlledExecutionDuplicateStatus,
    ControlledExecutionPipelineInput,
)


def build_controlled_execution_duplicate_guard_state(
    pipeline_input: ControlledExecutionPipelineInput,
) -> ControlledExecutionDuplicateGuardState:
    status = ControlledExecutionDuplicateStatus.NO_DUPLICATE
    if pipeline_input.approval_reuse_detected:
        status = ControlledExecutionDuplicateStatus.APPROVAL_REUSE_DETECTED
    elif pipeline_input.prior_pending_audit_unresolved:
        status = ControlledExecutionDuplicateStatus.PENDING_STATE_UNRESOLVED
    elif pipeline_input.prior_pending_draft_exists:
        status = ControlledExecutionDuplicateStatus.DUPLICATE_DRAFT
    elif pipeline_input.prior_open_intent_exists or pipeline_input.same_instrument_side_collision:
        status = ControlledExecutionDuplicateStatus.DUPLICATE_INTENT
    elif any(record.idempotency_key == pipeline_input.idempotency_key for record in pipeline_input.prior_audit_records if record.idempotency_key):
        status = ControlledExecutionDuplicateStatus.DUPLICATE_IDEMPOTENCY_KEY
    reason_codes = [] if status == ControlledExecutionDuplicateStatus.NO_DUPLICATE else [status.value]
    return ControlledExecutionDuplicateGuardState(
        state_id=f"{pipeline_input.pipeline_id}-DUPLICATE-GUARD-STATE",
        duplicate_status=status,
        idempotency_key=pipeline_input.idempotency_key,
        clear_for_preflight=status == ControlledExecutionDuplicateStatus.NO_DUPLICATE,
        reason_codes=reason_codes,
    )
