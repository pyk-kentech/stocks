from stock_risk_mcp.controlled_execution_duplicate_guard import build_controlled_execution_duplicate_guard_state
from stock_risk_mcp.controlled_execution_models import ControlledExecutionAuditRecord, ControlledExecutionPipelineInput
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_duplicate_guard_clear_when_unique():
    result = build_controlled_execution_duplicate_guard_state(ControlledExecutionPipelineInput.model_validate(controlled_execution_payload()))
    assert result.clear_for_preflight is True


def test_controlled_execution_duplicate_guard_detects_idempotency_reuse():
    payload = controlled_execution_payload(
        prior_audit_records=[
            ControlledExecutionAuditRecord.model_validate(
                {
                    "audit_id": "prior-audit-1",
                    "action_type": "PREFLIGHT",
                    "created_at": "2026-06-26T16:00:00+09:00",
                    "source_refs": ["fixtures/controlled_execution/prior.json"],
                    "idempotency_key": "IDEMPOTENCY-KEY-1",
                    "mode": "MOCK_EXECUTION_ONLY",
                    "decision": "PREFLIGHT_READY",
                    "reason_codes": ["OK"],
                }
            ).model_dump(mode="json")
        ]
    )
    result = build_controlled_execution_duplicate_guard_state(ControlledExecutionPipelineInput.model_validate(payload))
    assert result.clear_for_preflight is False
    assert result.duplicate_status == "DUPLICATE_IDEMPOTENCY_KEY"
