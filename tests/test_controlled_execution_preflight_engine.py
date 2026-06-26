from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput
from stock_risk_mcp.controlled_execution_preflight_engine import build_controlled_execution_preflight
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_preflight_builds_all_green_mock_pipeline():
    result = build_controlled_execution_preflight(ControlledExecutionPipelineInput.model_validate(controlled_execution_payload()), in_pytest=True)
    assert result.readiness_report.all_green is True
    assert result.preflight_decision.approved_for_draft is True
    assert result.kill_switch_state.clear_for_preflight is True
    assert result.duplicate_guard_state.clear_for_preflight is True
    assert result.order_draft.quantity == 1.0


def test_controlled_execution_preflight_blocks_leakage_or_stale_prerequisites():
    payload = controlled_execution_payload(
        leakage_report={"readiness_status": "BLOCKED_LEAKAGE"},
        account_read_report={"read_only": True, "account_ref_redacted": True, "stale": True},
    )
    result = build_controlled_execution_preflight(ControlledExecutionPipelineInput.model_validate(payload), in_pytest=True)
    assert result.readiness_report.all_green is False
    assert result.preflight_decision.approved_for_draft is False
    assert result.gap_report.gap_entries
