from stock_risk_mcp.controlled_execution_approval_engine import (
    build_controlled_execution_approval_packet,
    validate_controlled_execution_manual_approval,
)
from stock_risk_mcp.controlled_execution_models import ControlledExecutionOrderDraft, ControlledExecutionPipelineInput
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


def test_controlled_execution_approval_packet_and_manual_approval_bind_to_draft_hash():
    pipeline_input = ControlledExecutionPipelineInput.model_validate(controlled_execution_payload())
    draft = _draft()
    packet = build_controlled_execution_approval_packet(
        pipeline_input,
        draft,
        kill_switch_summary={"clear_for_preflight": True},
        duplicate_summary={"clear_for_preflight": True},
        risk_summary={"bounded_position_size": True},
        reconciliation_summary={"instrument_mapping_unambiguous": True},
        adapter_summary={"provider": "LOCAL_MOCK"},
    )
    approval = validate_controlled_execution_manual_approval(pipeline_input, draft, packet)
    assert packet.order_draft_hash == draft.draft_hash
    assert approval.order_draft_hash == draft.draft_hash
    assert approval.valid is True


def test_controlled_execution_manual_approval_blocks_reuse():
    payload = controlled_execution_payload(manual_approval_fixture={"approval_ref": "fake", "order_draft_hash": "DRAFT-CONTROLLED-EXECUTION-TEST-005930-BUY", "already_used": True})
    pipeline_input = ControlledExecutionPipelineInput.model_validate(payload)
    draft = _draft()
    packet = build_controlled_execution_approval_packet(
        pipeline_input,
        draft,
        kill_switch_summary={"clear_for_preflight": True},
        duplicate_summary={"clear_for_preflight": True},
        risk_summary={"bounded_position_size": True},
        reconciliation_summary={"instrument_mapping_unambiguous": True},
        adapter_summary={"provider": "LOCAL_MOCK"},
    )
    approval = validate_controlled_execution_manual_approval(pipeline_input, draft, packet)
    assert approval.valid is False
    assert "APPROVAL_REUSE_DETECTED" in approval.reason_codes
