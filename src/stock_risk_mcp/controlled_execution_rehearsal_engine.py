from __future__ import annotations

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionDryRunResult,
    ControlledExecutionMockExecutionResult,
    ControlledExecutionMode,
    ControlledExecutionOrderDraft,
    ControlledExecutionPipelineInput,
)


def build_controlled_execution_mock_execution_result(
    pipeline_input: ControlledExecutionPipelineInput,
    order_draft: ControlledExecutionOrderDraft,
    *,
    approval_valid: bool,
) -> ControlledExecutionMockExecutionResult:
    accepted = approval_valid and pipeline_input.mode in {
        ControlledExecutionMode.MOCK_EXECUTION_ONLY,
        ControlledExecutionMode.DRY_RUN_NO_BROKER,
        ControlledExecutionMode.MANUAL_APPROVAL_PACKET_ONLY,
        ControlledExecutionMode.PREFLIGHT_ONLY,
        ControlledExecutionMode.READINESS_REPORT_ONLY,
        ControlledExecutionMode.BLOCKED_DEFAULT,
    }
    return ControlledExecutionMockExecutionResult(
        result_id=f"{pipeline_input.pipeline_id}-MOCK-EXECUTION-RESULT",
        draft_id=order_draft.draft_id,
        simulated_status="MOCK_ACCEPTED" if accepted else "MOCK_REJECTED",
        accepted=accepted,
        audit_ref=f"{pipeline_input.pipeline_id}-MOCK-AUDIT",
        reason_codes=["APPROVAL_VALID" if approval_valid else "APPROVAL_INVALID"],
    )


def build_controlled_execution_dry_run_result(
    pipeline_input: ControlledExecutionPipelineInput,
    order_draft: ControlledExecutionOrderDraft,
    *,
    schema_evidence_present: bool,
) -> ControlledExecutionDryRunResult:
    return ControlledExecutionDryRunResult(
        result_id=f"{pipeline_input.pipeline_id}-DRY-RUN-RESULT",
        draft_id=order_draft.draft_id,
        preview_status="DRY_RUN_PREVIEW_READY" if schema_evidence_present else "DRY_RUN_SCHEMA_GAP",
        schema_evidence_present=schema_evidence_present,
        blocked_redacted_preview={
            "provider": pipeline_input.provider.value,
            "instrument_id": order_draft.instrument_id,
            "side": order_draft.side.value,
            "quantity": order_draft.quantity,
            "blocked": True,
            "non_executable": True,
        },
        audit_ref=f"{pipeline_input.pipeline_id}-DRY-RUN-AUDIT",
        reason_codes=["SCHEMA_EVIDENCE_PRESENT" if schema_evidence_present else "ADAPTER_SCHEMA_GAP"],
    )
