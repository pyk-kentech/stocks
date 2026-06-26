from stock_risk_mcp.controlled_execution_killswitch_engine import build_controlled_execution_kill_switch_state
from stock_risk_mcp.controlled_execution_models import ControlledExecutionPipelineInput
from tests.test_controlled_execution_models import controlled_execution_payload


def test_controlled_execution_kill_switch_clear_when_no_trips():
    result = build_controlled_execution_kill_switch_state(ControlledExecutionPipelineInput.model_validate(controlled_execution_payload()))
    assert result.clear_for_preflight is True
    assert result.reason_codes == []


def test_controlled_execution_kill_switch_blocks_on_daily_loss():
    payload = controlled_execution_payload(daily_loss_breached=True)
    result = build_controlled_execution_kill_switch_state(ControlledExecutionPipelineInput.model_validate(payload))
    assert result.clear_for_preflight is False
    assert "TRIPPED_DAILY_LOSS" in result.reason_codes
