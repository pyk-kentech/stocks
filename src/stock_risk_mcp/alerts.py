from datetime import datetime
from uuid import uuid4

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.models import BacktestOutcome
from stock_risk_mcp.pipeline_run import AlertSeverity, AlertType, PipelineAlert
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision
from stock_risk_mcp.setup import TradeDecision


def candidate_alerts(pipeline_run_id: str, candidates: list[CandidateScanResult]) -> list[PipelineAlert]:
    alerts = []
    included = [item for item in candidates if item.decision == CandidateDecision.INCLUDE]
    if included:
        alerts.append(_alert(pipeline_run_id, AlertType.CANDIDATE_FOUND, AlertSeverity.INFO, "Candidates found", f"{len(included)} INCLUDE candidates found."))
    for candidate in candidates:
        if candidate.metadata.get("signal_enrichment", {}).get("has_critical_negative"):
            alerts.append(_alert(pipeline_run_id, AlertType.SIGNAL_CRITICAL, AlertSeverity.CRITICAL, "Critical signal", f"{candidate.ticker} has a critical negative signal.", candidate.ticker))
    return alerts


def basket_alert(pipeline_run_id: str, decision: TradeDecision, allocation_count: int) -> PipelineAlert:
    if decision == TradeDecision.PROPOSE:
        return _alert(pipeline_run_id, AlertType.BASKET_PROPOSED, AlertSeverity.INFO, "Basket proposed", f"Basket proposal created with {allocation_count} allocations.")
    if decision == TradeDecision.REVIEW:
        return _alert(pipeline_run_id, AlertType.BASKET_PROPOSED, AlertSeverity.WARNING, "Basket review", f"Basket requires review with {allocation_count} allocations.")
    return _alert(pipeline_run_id, AlertType.BASKET_BLOCKED, AlertSeverity.WARNING, "Basket blocked", f"Basket decision is {decision.value}.")


def paper_alert(pipeline_run_id: str, result) -> PipelineAlert | None:
    if result.outcome == BacktestOutcome.WIN:
        return _alert(pipeline_run_id, AlertType.PAPER_WIN, AlertSeverity.INFO, "Paper outcome win", f"Paper return was {result.realized_return_pct:.4f}%.")
    if result.outcome == BacktestOutcome.LOSS:
        return _alert(pipeline_run_id, AlertType.PAPER_LOSS, AlertSeverity.WARNING, "Paper outcome loss", f"Paper return was {result.realized_return_pct:.4f}%.")
    return None


def policy_alert(pipeline_run_id: str, recommendation: PolicyEvaluationDecision) -> PipelineAlert:
    mapping = {
        PolicyEvaluationDecision.ACCEPT: (AlertType.POLICY_ACCEPT, AlertSeverity.HIGH),
        PolicyEvaluationDecision.REJECT: (AlertType.POLICY_REJECT, AlertSeverity.WARNING),
        PolicyEvaluationDecision.NEED_MORE_DATA: (AlertType.NEED_MORE_DATA, AlertSeverity.INFO),
    }
    alert_type, severity = mapping[recommendation]
    return _alert(pipeline_run_id, alert_type, severity, f"Policy evaluation {recommendation.value}", f"Policy suite recommendation is {recommendation.value}.")


def error_alert(pipeline_run_id: str, error: Exception | str) -> PipelineAlert:
    return _alert(pipeline_run_id, AlertType.PIPELINE_ERROR, AlertSeverity.CRITICAL, "Pipeline error", str(error))


def _alert(run_id, alert_type, severity, title, message, ticker=None):
    return PipelineAlert(
        alert_id=uuid4().hex, pipeline_run_id=run_id, alert_type=alert_type, severity=severity,
        ticker=ticker, title=title, message=message, created_at=datetime.now(),
    )
