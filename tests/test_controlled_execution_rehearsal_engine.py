from stock_risk_mcp.controlled_execution_models import ControlledExecutionOrderDraft, ControlledExecutionPipelineInput
from stock_risk_mcp.controlled_execution_rehearsal_engine import (
    build_controlled_execution_dry_run_result,
    build_controlled_execution_mock_execution_result,
)
from tests.test_controlled_execution_models import controlled_execution_payload


def _draft():
    return ControlledExecutionOrderDraft.model_validate(
        {
            "draft_id": "controlled-execution-test-order-draft",
            "instrument_id": "005930",
            "side": "BUY",
            "quantity": 1.0,
            "order_type": "LIMIT",
            "limit_price": 82450.0,
            "time_in_force": "DAY",
            "idempotency_key": "IDEMPOTENCY-KEY-1",
            "draft_hash": "DRAFT-CONTROLLED-EXECUTION-TEST-005930-BUY",
            "risk_checks": ["RISK-CHECK"],
            "reconciliation_checks": ["RECON-CHECK"],
            "adapter_target": "LOCAL_MOCK",
            "status": "PREFLIGHT_READY",
        }
    )


def test_controlled_execution_rehearsal_outputs_mock_and_dry_run_reports():
    pipeline_input = ControlledExecutionPipelineInput.model_validate(controlled_execution_payload())
    draft = _draft()
    mock_result = build_controlled_execution_mock_execution_result(pipeline_input, draft, approval_valid=True)
    dry_run = build_controlled_execution_dry_run_result(pipeline_input, draft, schema_evidence_present=True)
    assert mock_result.accepted is True
    assert dry_run.schema_evidence_present is True
    assert dry_run.blocked_redacted_preview["non_executable"] is True
