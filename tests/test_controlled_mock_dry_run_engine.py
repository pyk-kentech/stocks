from stock_risk_mcp.controlled_mock_dry_run_engine import build_controlled_mock_dry_run_review
from stock_risk_mcp.controlled_mock_dry_run_models import ControlledMockDryRunDecision, ControlledMockDryRunInput, MockIntentRouteType
from tests.test_controlled_mock_dry_run_models import controlled_mock_dry_run_payload


def _run(**overrides):
    payload = controlled_mock_dry_run_payload()
    payload.update(overrides)
    return build_controlled_mock_dry_run_review(ControlledMockDryRunInput.model_validate(payload))


def test_missing_v77_or_v78_dependency_causes_gap():
    result = _run(paper_evaluation_ref=None)
    assert result.summary_report.decision in {ControlledMockDryRunDecision.GAP, ControlledMockDryRunDecision.BLOCKED}


def test_mock_review_ready_can_be_dry_run_rehearsed_but_not_execution_ready():
    result = _run(mock_readiness_decision="MOCK_REVIEW_READY")
    assert result.summary_report.decision == ControlledMockDryRunDecision.DRY_RUN_REHEARSED


def test_mock_dry_run_ready_with_complete_evidence_can_be_execution_review_ready():
    result = _run()
    assert result.summary_report.decision == ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY


def test_failed_paper_pass_blocks():
    result = _run(paper_evaluation_decision="PAPER_FAIL")
    assert result.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_position_sizing_blocked_blocks():
    result = _run(position_sizing_decision="BLOCKED")
    assert result.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_position_sizing_size_ready_allows_preview():
    result = _run(position_sizing_decision="SIZE_READY")
    assert result.mock_order_intent_preview.quantity_preview == 50
    assert result.mock_order_intent_preview.notional_preview == 25000.0


def test_event_risk_block_new_entry_blocks_new_entry_preview():
    result = _run(event_risk_decision="BLOCK_NEW_ENTRY")
    assert result.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_event_risk_reduce_only_allows_only_exposure_reducing_rehearsal():
    reducing = _run(event_risk_decision="REDUCE_ONLY", candidate_is_exposure_reducing=True, candidate_action_type="TRIM")
    assert reducing.summary_report.decision in {ControlledMockDryRunDecision.DRY_RUN_REHEARSED, ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY}
    blocked = _run(event_risk_decision="REDUCE_ONLY", candidate_is_exposure_reducing=False)
    assert blocked.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_leadership_only_routes_only_leadership_candidate():
    result = _run(breadth_routing_decision="LEADERSHIP_ONLY", candidate_is_leadership=True)
    assert result.mock_order_intent_preview.route_type == MockIntentRouteType.LEADERSHIP_ONLY


def test_watch_non_leaders_prevents_non_leader_promotion():
    result = _run(breadth_routing_decision="WATCH_NON_LEADERS", candidate_is_leadership=False)
    assert result.summary_report.decision in {ControlledMockDryRunDecision.WATCH_ONLY, ControlledMockDryRunDecision.GAP}


def test_outlier_allowed_routes_to_outlier_sleeve_only():
    result = _run(
        breadth_routing_decision="OUTLIER_MOMENTUM_ALLOWED",
        candidate_is_outlier=True,
        route_hint="OUTLIER_MOMENTUM_SLEEVE",
    )
    assert result.mock_order_intent_preview.route_type == MockIntentRouteType.OUTLIER_MOMENTUM_SLEEVE


def test_outlier_restricted_reduces_or_watch_only():
    result = _run(
        breadth_routing_decision="OUTLIER_MOMENTUM_RESTRICTED",
        candidate_is_outlier=True,
        liquidity_evidence_ref=None,
    )
    assert result.summary_report.decision in {ControlledMockDryRunDecision.GAP, ControlledMockDryRunDecision.WATCH_ONLY, ControlledMockDryRunDecision.BLOCKED}


def test_block_chasing_blocks_crowded_leadership_chase():
    result = _run(breadth_routing_decision="BLOCK_CHASING")
    assert result.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_missing_opt_in_or_kill_switch_or_rollback_or_audit_policies_cause_gap_or_block():
    assert _run(opt_in_policy_ref=None).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(kill_switch_policy_ref=None).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(rollback_policy_ref=None).summary_report.decision in {ControlledMockDryRunDecision.GAP, ControlledMockDryRunDecision.BLOCKED}
    assert _run(audit_policy_ref=None).summary_report.decision in {ControlledMockDryRunDecision.GAP, ControlledMockDryRunDecision.BLOCKED}


def test_live_broker_kiwoom_provider_and_mock_order_dependencies_block():
    assert _run(live_prod_path_attempt=True).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(real_broker_dependency=True).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(kiwoom_dependency=True).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(provider_network_dependency=True).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(kiwoom_mock_order_execution_dependency=True).summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_real_order_id_presence_blocks():
    result = _run(real_order_id_present=True)
    assert result.summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_order_count_and_exposure_limits_are_enforced():
    assert _run(current_order_count=6).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(projected_total_exposure=0.7).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(candidate_is_inverse_or_hedge=True, projected_inverse_hedge_exposure=0.25).summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_outlier_sleeve_caps_are_enforced():
    assert _run(candidate_is_outlier=True, breadth_routing_decision="OUTLIER_MOMENTUM_ALLOWED", candidate_requested_sleeve_allocation=0.15).summary_report.decision == ControlledMockDryRunDecision.BLOCKED
    assert _run(candidate_is_outlier=True, breadth_routing_decision="OUTLIER_MOMENTUM_ALLOWED", candidate_requested_per_name_risk=0.02).summary_report.decision == ControlledMockDryRunDecision.BLOCKED


def test_mock_order_intents_remain_non_executable_previews():
    result = _run()
    assert result.mock_order_intent_preview.report_only is True
    assert result.mock_order_intent_preview.no_execution_flag is True


def test_boundary_violation_report_detects_unsafe_paths_and_audit_is_redacted():
    result = _run(real_broker_dependency=True)
    assert result.boundary_violation_report.real_broker_call_attempt is True
    assert result.audit_records[0].redaction_applied is True
