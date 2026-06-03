from __future__ import annotations

from stock_risk_mcp.adapters.mock_company_risk import MockCompanyRiskAdapter
from stock_risk_mcp.adapters.mock_market_data import MockMarketDataAdapter
from stock_risk_mcp.adapters.mock_toss_signal import MockTossSignalAdapter
from stock_risk_mcp.models import Decision
from stock_risk_mcp.scoring import calculate_soft_score
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_safe_ticker_is_allow_or_review() -> None:
    result = RiskEvaluationService(policy=make_policy()).evaluate(make_proposal("SAFE"))
    assert result.decision in {Decision.ALLOW, Decision.REVIEW}


def test_score_is_clamped_to_0_100() -> None:
    market = MockMarketDataAdapter().get_market_snapshot("SAFE")
    company = MockCompanyRiskAdapter().get_company_risk("SAFE")
    toss = MockTossSignalAdapter().get_toss_signal("SAFE")
    score = calculate_soft_score(market, company, toss).score
    assert 0 <= score <= 100
