from __future__ import annotations

from stock_risk_mcp.models import Decision, RiskResult
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_service_returns_risk_result() -> None:
    result = RiskEvaluationService(policy=make_policy()).evaluate(make_proposal("WATCH"))
    assert isinstance(result, RiskResult)
    assert result.decision in {Decision.ALLOW, Decision.REVIEW, Decision.BLOCK}
    assert result.beginner_summary
