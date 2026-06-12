from datetime import date, datetime, timedelta

import pytest

from stock_risk_mcp.asof_price_history import AsOfPriceHistoryProvider
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.policy_replay import replay_policy_on_replay_run
from stock_risk_mcp.policy_replay_result import PolicyReplayStatus
from stock_risk_mcp.replay_snapshot import (
    ReplayCandidateSnapshot,
    ReplayRun,
    ReplayRunStatus,
    ReplaySnapshotMode,
    ReplayTradePlanSnapshot,
)
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_policy import create_default_strategy_policy


def test_full_policy_replay_uses_candidate_universe_and_ignores_trade_snapshot(tmp_path) -> None:
    repository, run_id = _repository_with_replay_source(tmp_path)
    repository.save_replay_trade_plan_snapshot(
        ReplayTradePlanSnapshot(
            run_id=run_id,
            ticker="WRONG",
            decision="PROPOSE",
            snapshot_json={"ticker": "WRONG", "target_price": 999},
        )
    )

    execution = replay_policy_on_replay_run(
        repository=repository,
        price_provider=AsOfPriceHistoryProvider(repository=repository),
        source_replay_run_id=run_id,
        policy_id="default",
        policy_version="v1",
        horizon_days=10,
        account_equity=10_000,
        cash_available=5_000,
    )

    assert execution.result.status == PolicyReplayStatus.COMPLETED
    assert execution.result.trade_plan_count == 3
    assert all(plan.ticker in {"AAA", "BBB", "CCC"} for plan in execution.trade_plans)
    assert all(plan.policy_id == "default" and plan.setup_scoring_mode == "POLICY_WEIGHTED" for plan in execution.trade_plans)
    assert execution.basket.policy_id == "default"


def test_full_policy_replay_storage_is_opt_in(tmp_path) -> None:
    repository, run_id = _repository_with_replay_source(tmp_path)
    provider = AsOfPriceHistoryProvider(repository=repository)

    memory_only = replay_policy_on_replay_run(
        repository, provider, run_id, "default", "v1", 10, 10_000, 5_000
    )

    assert memory_only.save_intermediate is False
    assert memory_only.saved_trade_plan_count == 0
    assert memory_only.saved_to_basket_plans is False
    assert repository.count_rows("trade_plans") == 0
    assert repository.count_rows("basket_plans") == 0

    saved = replay_policy_on_replay_run(
        repository, provider, run_id, "default", "v1", 10, 10_000, 5_000,
        save_intermediate=True, save_basket=True,
    )

    assert saved.saved_trade_plan_count == 3
    assert saved.saved_to_basket_plans is True
    assert repository.count_rows("trade_plans") == 3
    assert repository.count_rows("basket_plans") == 1
    assert repository.count_rows("indicator_values") == 0
    assert all(
        plan.policy_id == "default"
        and plan.policy_version == "v1"
        and plan.setup_scoring_mode == "POLICY_WEIGHTED"
        for plan in repository.list_trade_plans()
    )
    assert any("without policy_replay_id linkage" in note for note in saved.result.notes)


def test_full_policy_replay_saves_no_data_when_history_is_insufficient(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    policy = create_default_strategy_policy()
    repository.save_strategy_policy(policy)
    run_id = _save_source_run(repository, ["AAA"])
    repository.save_price_bars(_bars("AAA", date(2026, 1, 1), 20))

    execution = replay_policy_on_replay_run(
        repository, AsOfPriceHistoryProvider(repository=repository), run_id,
        "default", "v1", 10, 10_000, 5_000,
    )

    assert execution.result.status == PolicyReplayStatus.NO_DATA
    assert repository.get_policy_replay_result(execution.result.policy_replay_id) == execution.result


def test_full_policy_replay_saves_failed_result_for_unexpected_execution_error(tmp_path) -> None:
    repository, run_id = _repository_with_replay_source(tmp_path)

    class BrokenProvider:
        def get_history_until(self, ticker, as_of_date, min_bars=120):
            raise RuntimeError("broken price provider")

    with pytest.raises(RuntimeError, match="broken price provider"):
        replay_policy_on_replay_run(
            repository, BrokenProvider(), run_id, "default", "v1", 10, 10_000, 5_000
        )

    assert repository.list_policy_replay_results(run_id)[0].status == PolicyReplayStatus.FAILED


def _repository_with_replay_source(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_strategy_policy(create_default_strategy_policy())
    run_id = _save_source_run(repository, ["AAA", "BBB", "CCC"])
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_price_bars(_bars(ticker, date(2025, 9, 1), 150))
    return repository, run_id


def _save_source_run(repository, tickers: list[str]) -> str:
    run_id = "source-run"
    repository.save_replay_run(
        ReplayRun(
            run_id=run_id,
            status=ReplayRunStatus.COMPLETED,
            snapshot_mode=ReplaySnapshotMode.FIXED_RULES,
            source_type="RECENT_TRADE_PLANS",
            as_of_date=date(2026, 1, 5),
            notes=[],
            created_at=datetime(2026, 1, 5),
        )
    )
    for ticker in tickers:
        repository.save_replay_candidate_snapshot(
            ReplayCandidateSnapshot(
                run_id=run_id,
                ticker=ticker,
                source="fixture",
                snapshot_json={"ticker": ticker, "sector": "TECH", "theme": "AI"},
            )
        )
    return run_id


def _bars(ticker: str, start: date, count: int) -> list[PriceBar]:
    return [
        PriceBar(
            ticker=ticker,
            date=start + timedelta(days=index),
            open=10 + index * 0.1,
            high=10.8 + index * 0.1,
            low=9.8 + index * 0.1,
            close=10.5 + index * 0.1,
            volume=5_000_000 + index * 100_000,
        )
        for index in range(count)
    ]
