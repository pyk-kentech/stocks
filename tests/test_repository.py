from __future__ import annotations

from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.models import NewsEvent
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_repository_saves_evaluation_inputs_and_result(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = RiskEvaluationService(policy=make_policy())
    context = service.evaluate_with_context(make_proposal("SAFE"))

    saved = save_evaluation_inputs_and_result(
        repository=repository,
        proposal=context.proposal,
        policy=context.policy,
        market=context.market,
        company=context.company,
        toss_signal=context.toss_signal,
        result=context.result,
        news_events=[
            NewsEvent(
                ticker="SAFE",
                headline="SAFE reports steady operating update",
                source="fixture",
            )
        ],
        source="test",
    )

    assert saved.evaluation_id == 1
    assert repository.count_rows("market_snapshots") == 1
    assert repository.count_rows("company_risks") == 1
    assert repository.count_rows("toss_investor_snapshots") == 1
    assert repository.count_rows("news_events") == 1
    assert repository.count_rows("risk_evaluations") == 1
