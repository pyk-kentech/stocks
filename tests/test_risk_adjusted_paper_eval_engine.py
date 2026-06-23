from stock_risk_mcp.risk_adjusted_paper_eval_engine import build_risk_adjusted_paper_evaluation
from stock_risk_mcp.risk_adjusted_paper_eval_models import RiskAdjustedPaperEvalDecision, RiskAdjustedPaperEvalInput
from tests.test_risk_adjusted_paper_eval_models import risk_adjusted_paper_eval_payload


def _evaluate(**overrides):
    payload = risk_adjusted_paper_eval_payload()
    payload.update(overrides)
    return build_risk_adjusted_paper_evaluation(RiskAdjustedPaperEvalInput.model_validate(payload))


def test_missing_v76_policy_dependency_causes_gap():
    result = _evaluate(allocation_policy_candidate_ref=None)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.GAP


def test_policy_below_trained_offline_is_blocked_or_research_only():
    result = _evaluate(policy_promotion_decision="RESEARCH_ONLY")
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.RESEARCH_ONLY


def test_valid_local_fixture_can_produce_paper_evaluated():
    result = _evaluate(policy_promotion_decision="TRAINED_OFFLINE", end_price=71000.0)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.PAPER_EVALUATED


def test_strong_cost_adjusted_fixture_can_produce_paper_pass():
    result = _evaluate(policy_promotion_decision="PAPER_CANDIDATE", end_price=76000.0, volatility=0.05)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.PAPER_PASS


def test_missing_cost_slippage_assumptions_prevents_paper_pass():
    result = _evaluate(policy_promotion_decision="PAPER_CANDIDATE", end_price=76000.0, fee_tax_slippage_assumptions_ref=None)
    assert result.pass_readiness_report.decision != RiskAdjustedPaperEvalDecision.PAPER_PASS


def test_future_price_leakage_is_blocked():
    result = _evaluate(future_price_leakage_detected=True)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.BLOCKED


def test_future_regime_fear_leakage_is_blocked():
    result = _evaluate(future_regime_fear_leakage_detected=True)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.BLOCKED


def test_max_drawdown_breach_blocks_paper_pass():
    result = _evaluate(end_price=50000.0)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.BLOCKED


def test_daily_loss_breach_blocks_paper_pass():
    result = _evaluate(end_price=65000.0, daily_loss_limit=0.01)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.BLOCKED


def test_excessive_turnover_blocks_or_downgrades():
    result = _evaluate(turnover=0.95)
    assert result.pass_readiness_report.decision in {RiskAdjustedPaperEvalDecision.PAPER_EVALUATED, RiskAdjustedPaperEvalDecision.BLOCKED}


def test_excessive_inverse_hedge_exposure_blocks_paper_pass():
    result = _evaluate(inverse_hedge_exposure=0.35)
    assert result.pass_readiness_report.decision == RiskAdjustedPaperEvalDecision.BLOCKED


def test_virtual_orders_trades_are_explicitly_simulated_and_non_executable():
    result = _evaluate()
    assert result.virtual_portfolio_report.virtual_orders[0].executable is False
    assert result.virtual_portfolio_report.virtual_trades[0].executable is False


def test_cnn_feature_integrates_into_fear_bucket_report_when_present():
    result = _evaluate()
    assert result.regime_fear_bucket_report.cnn_fear_greed_feature_used is True
    assert "FEAR" in result.regime_fear_bucket_report.fear_bucket_performance


def test_missing_cnn_feature_creates_gap_note_but_does_not_automatically_block():
    result = _evaluate(cnn_fear_greed_feature_ref=None, fear_bucket_name=None, end_price=71000.0)
    assert result.regime_fear_bucket_report.missing_cnn_feature_gap_noted is True
    assert result.pass_readiness_report.decision != RiskAdjustedPaperEvalDecision.BLOCKED


def test_audit_report_is_redacted():
    result = _evaluate()
    assert result.audit_records[0].redaction_applied is True
    assert result.audit_records[0].contains_secret_material is False
