from __future__ import annotations

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionKillSwitchState,
    ControlledExecutionKillSwitchStatus,
    ControlledExecutionPipelineInput,
)


def build_controlled_execution_kill_switch_state(
    pipeline_input: ControlledExecutionPipelineInput,
) -> ControlledExecutionKillSwitchState:
    global_status = ControlledExecutionKillSwitchStatus.ACTIVE if pipeline_input.global_kill_switch_active else ControlledExecutionKillSwitchStatus.CLEAR
    market_status = ControlledExecutionKillSwitchStatus.ACTIVE if pipeline_input.market_kill_switch_active else ControlledExecutionKillSwitchStatus.CLEAR
    instrument_status = ControlledExecutionKillSwitchStatus.ACTIVE if pipeline_input.instrument_kill_switch_active else ControlledExecutionKillSwitchStatus.CLEAR
    daily_loss_status = ControlledExecutionKillSwitchStatus.TRIPPED_DAILY_LOSS if pipeline_input.daily_loss_breached else ControlledExecutionKillSwitchStatus.CLEAR
    max_order_count_status = ControlledExecutionKillSwitchStatus.TRIPPED_MAX_ORDERS if pipeline_input.max_order_count_breached else ControlledExecutionKillSwitchStatus.CLEAR
    max_exposure_status = ControlledExecutionKillSwitchStatus.TRIPPED_MAX_EXPOSURE if pipeline_input.max_exposure_breached else ControlledExecutionKillSwitchStatus.CLEAR
    event_risk_status = ControlledExecutionKillSwitchStatus.TRIPPED_EVENT_RISK if str(pipeline_input.event_risk_report.get("decision", "")).upper() in {"BLOCK_NEW_ENTRY", "BLOCKED", "REJECTED"} else ControlledExecutionKillSwitchStatus.CLEAR
    stale_data_status = ControlledExecutionKillSwitchStatus.TRIPPED_STALE_DATA if pipeline_input.stale_data_blocked else ControlledExecutionKillSwitchStatus.CLEAR
    cooldown_status = ControlledExecutionKillSwitchStatus.ACTIVE if pipeline_input.cooldown_active else ControlledExecutionKillSwitchStatus.CLEAR
    statuses = (
        global_status,
        market_status,
        instrument_status,
        daily_loss_status,
        max_order_count_status,
        max_exposure_status,
        event_risk_status,
        stale_data_status,
        cooldown_status,
    )
    reason_codes = [status.value for status in statuses if status != ControlledExecutionKillSwitchStatus.CLEAR]
    return ControlledExecutionKillSwitchState(
        state_id=f"{pipeline_input.pipeline_id}-KILL-SWITCH-STATE",
        global_status=global_status,
        market_status=market_status,
        instrument_status=instrument_status,
        daily_loss_status=daily_loss_status,
        max_order_count_status=max_order_count_status,
        max_exposure_status=max_exposure_status,
        event_risk_status=event_risk_status,
        stale_data_status=stale_data_status,
        cooldown_status=cooldown_status,
        clear_for_preflight=not reason_codes,
        reason_codes=reason_codes,
    )
