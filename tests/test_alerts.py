from datetime import date, datetime

from stock_risk_mcp.alerts import candidate_alerts, paper_alert, policy_alert
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.paper_trading import BasketBacktestResult
from stock_risk_mcp.pipeline_run import AlertType
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision


def test_alert_generation_for_candidates_paper_and_policy() -> None:
    candidate = CandidateScanResult(
        scan_run_id="scan", ticker="AAA", as_of_date=date(2026, 1, 1),
        decision=CandidateDecision.INCLUDE, score=80,
        metadata={"signal_enrichment": {"has_critical_negative": True}},
    )
    alerts = candidate_alerts("pipe", [candidate])
    loss = paper_alert("pipe", _paper(BacktestOutcome.LOSS))
    accepted = policy_alert("pipe", PolicyEvaluationDecision.ACCEPT)
    no_data = paper_alert("pipe", _paper(BacktestOutcome.NO_DATA))

    assert {item.alert_type for item in alerts} == {AlertType.CANDIDATE_FOUND, AlertType.SIGNAL_CRITICAL}
    assert loss.alert_type == AlertType.PAPER_LOSS
    assert accepted.alert_type == AlertType.POLICY_ACCEPT
    assert no_data is None


def _paper(outcome):
    return BasketBacktestResult(
        basket_id="basket", horizon_days=10, entry_date=date(2026, 1, 1),
        total_notional_value=100, total_allocated_loss=10, realized_pnl=-5,
        realized_return_pct=-5, win_count=0, loss_count=1, flat_count=0,
        no_data_count=0, closed_trade_count=1, outcome=outcome, created_at=datetime(2026, 1, 2),
    )
