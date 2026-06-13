from datetime import date, timedelta

from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.operational_pipeline import OperationalPipeline
from stock_risk_mcp.pipeline_run import AlertType, PipelineRunStatus
from stock_risk_mcp.policy_replay_result import PolicyReplayMode, PolicyReplayResult, PolicyReplayStatus
from stock_risk_mcp.repository import RiskRepository
from datetime import datetime


def test_scan_only_pipeline_saves_run_scan_and_candidate_alert(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_price_bars(_bars("AAA"))

    execution = OperationalPipeline(repository).run_scan_only_pipeline(date(2026, 1, 20), tickers=["AAA"])

    assert execution.run.scan_run_id is not None
    assert execution.run.status == PipelineRunStatus.COMPLETED
    assert any(item.alert_type == AlertType.CANDIDATE_FOUND for item in execution.alerts)
    assert repository.count_rows("pipeline_runs") == 1


def test_paper_pipeline_keeps_memory_result_unless_basket_is_saved(tmp_path) -> None:
    memory_repo = RiskRepository(tmp_path / "memory.sqlite3")
    saved_repo = RiskRepository(tmp_path / "saved.sqlite3")
    for repository in (memory_repo, saved_repo):
        for ticker in ("AAA", "BBB", "CCC"):
            repository.save_price_bars(_bars(ticker))

    memory = OperationalPipeline(memory_repo).run_paper_basket_pipeline(
        date(2026, 1, 20), 10_000, 5_000, 10, tickers=["AAA", "BBB", "CCC"], save_basket=False,
    )
    saved = OperationalPipeline(saved_repo).run_paper_basket_pipeline(
        date(2026, 1, 20), 10_000, 5_000, 10, tickers=["AAA", "BBB", "CCC"], save_basket=True,
    )

    assert memory.paper_result is not None
    assert memory.paper_result_persisted is False
    assert memory_repo.count_rows("paper_trades") == 0
    assert memory_repo.count_rows("basket_backtest_results") == 0
    assert memory.summary.paper_outcome is not None
    assert "paper trading result was computed in memory because save_basket=false" in memory.run.notes
    assert "Replay snapshot basket_id may not exist in basket_plans." in memory_repo.get_replay_run(memory.run.replay_run_id).notes
    assert saved.paper_result_persisted is True
    assert saved_repo.count_rows("paper_trades") > 0
    assert saved_repo.count_rows("basket_backtest_results") == 1
    assert "Basket was also saved to basket_plans." in saved_repo.get_replay_run(saved.run.replay_run_id).notes


def test_paper_pipeline_can_skip_paper_and_reports_no_candidates(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    skipped = OperationalPipeline(repository).run_paper_basket_pipeline(
        date(2026, 1, 20), 10_000, 5_000, 10, tickers=[], paper_trade=False,
    )

    assert skipped.run.status == PipelineRunStatus.NO_CANDIDATES
    assert skipped.paper_result is None
    assert "paper trading skipped by option" in skipped.run.notes


def test_paper_pipeline_skips_calculation_for_eligible_candidates(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker))

    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        date(2026, 1, 20), 10_000, 5_000, 10, tickers=["AAA", "BBB", "CCC"], paper_trade=False,
    )

    assert execution.paper_result is None
    assert execution.summary.paper_outcome is None
    assert repository.count_rows("paper_trades") == 0
    assert "paper trading skipped by option" in execution.run.notes


def test_policy_evaluation_pipeline_saves_suite_and_recommendation_alert(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    for index in range(5):
        repository.save_policy_replay_result(_replay(f"r{index}", "v1", 50, 1))
        repository.save_policy_replay_result(_replay(f"r{index}", "v2", 56, 3))

    execution = OperationalPipeline(repository).run_replay_evaluation_pipeline(
        [f"r{index}" for index in range(5)], "default", "v1", "default", "v2", 10, 10_000, 5_000,
    )

    assert execution.run.status == PipelineRunStatus.COMPLETED
    assert execution.run.evaluation_suite_id is not None
    assert any(item.alert_type == AlertType.POLICY_ACCEPT for item in execution.alerts)
    assert repository.count_rows("policy_promotion_proposals") == 0


def test_paper_pipeline_records_partial_when_basket_stage_fails(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_price_bars(_bars("AAA"))

    execution = OperationalPipeline(repository).run_paper_basket_pipeline(
        date(2026, 1, 20), -1, 5_000, 10, tickers=["AAA"],
    )

    assert execution.run.status == PipelineRunStatus.PARTIAL
    assert execution.run.scan_run_id is not None
    assert any(item.alert_type == AlertType.PIPELINE_ERROR for item in execution.alerts)


def _bars(ticker):
    start = date(2025, 9, 1)
    bars = [
        PriceBar(
            ticker=ticker, date=start + timedelta(days=i),
            open=100+i*.02+(0.5 if i % 2 else 0),
            high=101+i*.02+(0.5 if i % 2 else 0),
            low=99+i*.02+(0.5 if i % 2 else 0),
            close=100+i*.02+(0.5 if i % 2 else 0),
            volume=3_000_000 if i < 139 else 12_000_000,
        )
        for i in range(140)
    ]
    bars.extend([
        PriceBar(ticker=ticker, date=date(2026, 1, 21), low=20, high=40, close=35, volume=10_000_000),
        PriceBar(ticker=ticker, date=date(2026, 1, 22), low=20, high=45, close=40, volume=10_000_000),
    ])
    return bars


def _replay(run_id, version, objective, return_pct):
    return PolicyReplayResult(
        policy_replay_id=f"{run_id}-{version}", source_replay_run_id=run_id,
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY, policy_id="default", policy_version=version,
        as_of_date=date(2026, 1, 1), horizon_days=10, candidate_count=3, trade_plan_count=3,
        realized_return_pct=return_pct, objective_score=objective, win_count=2, loss_count=1,
        no_data_count=0, status=PolicyReplayStatus.COMPLETED, notes=[], created_at=datetime(2026, 1, 2),
    )
