from __future__ import annotations

from stock_risk_mcp.ingestion import save_evaluation_inputs_and_result
from stock_risk_mcp.models import BacktestOutcome, BacktestResult, Decision, ReasonType, Severity
from stock_risk_mcp.reason_codes import HardBlockCode
from stock_risk_mcp.reporting import ReportService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.service import RiskEvaluationService

from tests.utils import make_policy, make_proposal


def test_bad_ticker_saves_nasdaq_noncompliant_reason_code(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    saved = _evaluate_and_save(repository, "BAD")

    reasons = repository.get_evaluation_reasons(saved.evaluation_id)

    assert any(reason.reason_code == HardBlockCode.NASDAQ_NONCOMPLIANT.value for reason in reasons)
    reason = next(reason for reason in reasons if reason.reason_code == HardBlockCode.NASDAQ_NONCOMPLIANT.value)
    assert reason.reason_type == ReasonType.HARD_BLOCK
    assert reason.severity == Severity.CRITICAL
    assert reason.evidence is not None
    assert reason.evidence.source_name == "mock_company_risk"


def test_dilute_and_pump_reason_codes_are_saved(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    dilute = _evaluate_and_save(repository, "DILUTE")
    pump = _evaluate_and_save(repository, "PUMP")

    dilute_codes = {reason.reason_code for reason in repository.get_evaluation_reasons(dilute.evaluation_id)}
    pump_codes = {reason.reason_code for reason in repository.get_evaluation_reasons(pump.evaluation_id)}

    assert HardBlockCode.DILUTION_RISK_HIGH.value in dilute_codes
    assert HardBlockCode.RETURN_5D_TOO_HIGH.value in pump_codes


def test_evaluation_reasons_can_be_saved_and_queried_by_code(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    saved = _evaluate_and_save(repository, "BAD")

    by_code = repository.get_reasons_by_code(HardBlockCode.NASDAQ_NONCOMPLIANT.value)

    assert len(by_code) == 1
    assert by_code[0].risk_evaluation_id == saved.evaluation_id
    assert by_code[0].ticker == "BAD"


def test_reporting_prefers_normalized_evaluation_reasons(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    saved = _evaluate_and_save(repository, "BAD")
    repository.save_backtest_result(
        BacktestResult(
            risk_evaluation_id=saved.evaluation_id,
            ticker="BAD",
            decision=Decision.BLOCK,
            score=30,
            horizon_days=30,
            entry_price=10,
            exit_price=8,
            return_pct=-20,
            max_drawdown_pct=-30,
            max_gain_pct=1,
            outcome=BacktestOutcome.LOSS,
        )
    )

    hard_blocks = ReportService(repository=repository).hard_block_performance()

    assert HardBlockCode.NASDAQ_NONCOMPLIANT.value in hard_blocks
    assert hard_blocks[HardBlockCode.NASDAQ_NONCOMPLIANT.value]["count"] == 1


def test_reporting_falls_back_to_result_json_when_reasons_table_is_empty(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    context = RiskEvaluationService(policy=make_policy()).evaluate_with_context(make_proposal("BAD"))
    evaluation_id = repository.save_risk_evaluation(
        proposal=context.proposal,
        policy=context.policy,
        result=context.result,
        market_snapshot_id=repository.save_market_snapshot(context.market),
        company_risk_id=repository.save_company_risk(context.company),
        toss_investor_snapshot_id=repository.save_toss_signal(context.proposal.ticker, context.toss_signal),
    )
    repository.save_backtest_result(
        BacktestResult(
            risk_evaluation_id=evaluation_id,
            ticker="BAD",
            decision=Decision.BLOCK,
            score=30,
            horizon_days=30,
            entry_price=10,
            exit_price=8,
            return_pct=-20,
            max_drawdown_pct=-30,
            max_gain_pct=1,
            outcome=BacktestOutcome.LOSS,
        )
    )

    hard_blocks = ReportService(repository=repository).hard_block_performance()

    assert HardBlockCode.NASDAQ_NONCOMPLIANT.value in hard_blocks


def _evaluate_and_save(repository: RiskRepository, ticker: str):
    context = RiskEvaluationService(policy=make_policy()).evaluate_with_context(make_proposal(ticker))
    return save_evaluation_inputs_and_result(
        repository=repository,
        proposal=context.proposal,
        policy=context.policy,
        market=context.market,
        company=context.company,
        toss_signal=context.toss_signal,
        result=context.result,
    )
