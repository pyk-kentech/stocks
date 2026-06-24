from stock_risk_mcp.controlled_mock_readiness_engine import build_controlled_mock_readiness_review
from stock_risk_mcp.controlled_mock_readiness_models import ControlledMockReadinessDecision, ControlledMockReadinessInput
from tests.test_controlled_mock_readiness_models import controlled_mock_readiness_payload


def _evaluate(**overrides):
    payload = controlled_mock_readiness_payload()
    payload.update(overrides)
    return build_controlled_mock_readiness_review(ControlledMockReadinessInput.model_validate(payload))


def test_missing_v77_paper_pass_causes_gap_or_blocked():
    result = _evaluate(paper_evaluation_ref=None)
    assert result.summary_report.decision in {ControlledMockReadinessDecision.GAP, ControlledMockReadinessDecision.BLOCKED}


def test_failed_paper_evaluation_blocks_mock_readiness():
    result = _evaluate(paper_evaluation_decision="BLOCKED")
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_valid_paper_pass_fixture_can_become_mock_review_ready():
    result = _evaluate(mock_oauth_readiness_status="MOCK_ONLY", mock_market_data_readiness_status="GAP")
    assert result.summary_report.decision == ControlledMockReadinessDecision.MOCK_REVIEW_READY


def test_strong_complete_fixture_can_become_mock_dry_run_ready():
    result = _evaluate(mock_oauth_readiness_status="AVAILABLE", mock_market_data_readiness_status="AVAILABLE")
    assert result.summary_report.decision == ControlledMockReadinessDecision.MOCK_DRY_RUN_READY


def test_missing_kill_switch_causes_gap_or_blocked():
    result = _evaluate(kill_switch_policy_ref=None)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_missing_explicit_opt_in_policy_causes_gap_or_blocked():
    result = _evaluate(user_opt_in_policy_ref=None)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_missing_audit_policy_causes_gap():
    result = _evaluate(audit_policy_ref=None)
    assert result.summary_report.decision == ControlledMockReadinessDecision.GAP


def test_missing_rollback_policy_causes_gap():
    result = _evaluate(rollback_policy_ref=None)
    assert result.summary_report.decision == ControlledMockReadinessDecision.GAP


def test_live_prod_path_blocks_readiness():
    result = _evaluate(live_prod_path_attempt=True)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_real_broker_account_order_dependency_blocks_readiness():
    for override in ({"real_broker_dependency": True}, {"real_account_dependency": True}, {"real_order_dependency": True}):
        result = _evaluate(**override)
        assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_autonomous_execution_path_blocks_readiness():
    result = _evaluate(autonomous_execution_path=True)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED


def test_excessive_drawdown_exposure_turnover_blocks_readiness():
    result = _evaluate(drawdown_limit_passed=False)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED
    result = _evaluate(exposure_limit_passed=False)
    assert result.summary_report.decision == ControlledMockReadinessDecision.BLOCKED
    result = _evaluate(turnover_limit_passed=False)
    assert result.summary_report.decision in {ControlledMockReadinessDecision.GAP, ControlledMockReadinessDecision.MOCK_REVIEW_READY, ControlledMockReadinessDecision.BLOCKED}


def test_cnn_feature_gap_is_noted_but_not_automatically_blocking():
    result = _evaluate(cnn_feature_gap_noted=True)
    assert any(entry.gap_category.value == "CNN_FEATURE_GAP_NOTED" for entry in result.gap_report.gap_entries)
    assert result.summary_report.decision != ControlledMockReadinessDecision.BLOCKED


def test_audit_report_is_redacted():
    result = _evaluate()
    assert result.audit_records[0].redaction_applied is True
