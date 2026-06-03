from __future__ import annotations

from stock_risk_mcp.models import BacktestOutcome, BacktestResult, Decision
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_report_returns_empty_sections_without_data(tmp_path) -> None:
    report = ReportService(repository=RiskRepository(tmp_path / "risk.sqlite3")).full_report()

    assert report == {
        "decision_performance": {},
        "score_bucket_performance": {},
        "hard_block_performance": {},
        "policy_recommendations": [],
    }


def test_report_decision_and_score_bucket_performance(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    _save_report_row(repository, "SAFE", 90, Decision.ALLOW, [], 10, BacktestOutcome.WIN, -2, 14)
    _save_report_row(repository, "WATCH", 70, Decision.REVIEW, [], 2, BacktestOutcome.FLAT, -5, 6)
    _save_report_row(
        repository,
        "BAD",
        50,
        Decision.BLOCK,
        ["Nasdaq noncompliant"],
        -8,
        BacktestOutcome.LOSS,
        -20,
        1,
    )
    service = ReportService(repository=repository)

    decision = service.decision_performance()
    buckets = service.score_bucket_performance()

    assert decision["ALLOW"]["avg_return_pct"] == 10.0
    assert decision["ALLOW"]["win_rate"] == 1.0
    assert decision["BLOCK"]["loss_rate"] == 1.0
    assert decision["BLOCK"]["worst_return_pct"] == -8.0
    assert buckets["80_100"]["count"] == 1
    assert buckets["60_79"]["count"] == 1
    assert buckets["40_59"]["count"] == 1


def test_report_hard_block_performance_and_recommendations(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for index in range(5):
        _save_report_row(
            repository,
            f"DIL{index}",
            45,
            Decision.BLOCK,
            ["dilution risk HIGH"],
            -6 - index,
            BacktestOutcome.LOSS,
            -15 - index,
            2,
        )
    for index in range(5):
        _save_report_row(
            repository,
            f"PMP{index}",
            55,
            Decision.BLOCK,
            ["5d return too high"],
            4 + index,
            BacktestOutcome.WIN,
            -3,
            10,
        )
    service = ReportService(repository=repository)

    hard_blocks = service.hard_block_performance()
    recommendations = service.generate_policy_recommendations()

    assert hard_blocks["DILUTION_RISK_HIGH"]["count"] == 5
    assert hard_blocks["DILUTION_RISK_HIGH"]["avg_return_pct"] == -8.0
    assert hard_blocks["RETURN_5D_TOO_HIGH"]["win_rate"] == 1.0
    assert "DILUTION_RISK_HIGH 차단 규칙은 유효해 보입니다." in recommendations
    assert "RETURN_5D_TOO_HIGH 차단 규칙은 너무 보수적일 수 있습니다." in recommendations


def _save_report_row(
    repository: RiskRepository,
    ticker: str,
    score: int,
    decision: Decision,
    hard_blocks: list[str],
    return_pct: float,
    outcome: BacktestOutcome,
    max_drawdown_pct: float,
    max_gain_pct: float,
) -> None:
    context = RiskEvaluationService(policy=make_policy()).evaluate_with_context(make_proposal("SAFE"))
    result = context.result.model_copy(
        update={
            "ticker": ticker,
            "decision": decision,
            "score": score,
            "hard_blocks": hard_blocks,
        }
    )
    proposal = context.proposal.model_copy(update={"ticker": ticker})
    market = context.market.model_copy(update={"ticker": ticker})
    company = context.company.model_copy(update={"ticker": ticker})
    evaluation_id = repository.save_risk_evaluation(
        proposal=proposal,
        policy=context.policy,
        result=result,
        market_snapshot_id=repository.save_market_snapshot(market),
        company_risk_id=repository.save_company_risk(company),
        toss_investor_snapshot_id=repository.save_toss_signal(ticker, context.toss_signal),
    )
    repository.save_backtest_result(
        BacktestResult(
            risk_evaluation_id=evaluation_id,
            ticker=ticker,
            decision=decision,
            score=score,
            horizon_days=30,
            entry_price=100,
            exit_price=100 + return_pct,
            return_pct=return_pct,
            max_drawdown_pct=max_drawdown_pct,
            max_gain_pct=max_gain_pct,
            outcome=outcome,
        )
    )
