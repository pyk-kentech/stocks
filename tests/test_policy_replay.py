import json
from datetime import date, datetime, timedelta

from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.replay_snapshot import ReplayCandidateSnapshot, ReplayRun, ReplayRunStatus, ReplaySnapshotMode
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_policy import create_default_strategy_policy


def test_policy_replay_cli_commands(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db_path)
    repository.save_strategy_policy(create_default_strategy_policy())
    run_id = _source(repository)
    common = [
        "--db", str(db_path), "--replay-run-id", run_id, "--horizon-days", "10",
        "--account-equity", "10000", "--cash-available", "5000",
    ]

    main(["policy-replay", *common, "--policy-id", "default", "--policy-version", "v1"])
    replay = json.loads(capsys.readouterr().out)
    main(["policy-replay-active", *common])
    active = json.loads(capsys.readouterr().out)
    main(["policy-replay-results", "--db", str(db_path), "--replay-run-id", run_id])
    results = json.loads(capsys.readouterr().out)
    main(
        [
            "policy-compare", *common,
            "--baseline-policy-id", "default", "--baseline-policy-version", "v1",
            "--candidate-policy-id", "default", "--candidate-policy-version", "v1",
        ]
    )
    comparison = json.loads(capsys.readouterr().out)

    assert replay["save_intermediate"] is False
    assert replay["saved_trade_plan_count"] == 0
    assert replay["saved_to_basket_plans"] is False
    assert active["result"]["policy_id"] == "default"
    assert len(results["results"]) >= 2
    assert comparison["baseline"]["policy_id"] == "default"
    assert comparison["candidate"]["policy_id"] == "default"


def _source(repository: RiskRepository) -> str:
    run_id = "source-cli"
    cutoff = date(2026, 1, 5)
    repository.save_replay_run(
        ReplayRun(
            run_id=run_id,
            status=ReplayRunStatus.COMPLETED,
            snapshot_mode=ReplaySnapshotMode.FIXED_RULES,
            source_type="fixture",
            as_of_date=cutoff,
            notes=[],
            created_at=datetime(2026, 1, 5),
        )
    )
    for ticker in ("AAA", "BBB", "CCC"):
        repository.save_replay_candidate_snapshot(
            ReplayCandidateSnapshot(run_id=run_id, ticker=ticker, source="fixture", snapshot_json={"ticker": ticker})
        )
        repository.save_price_bars(
            [
                PriceBar(
                    ticker=ticker,
                    date=date(2025, 9, 1) + timedelta(days=index),
                    open=10 + index * 0.1,
                    high=10.8 + index * 0.1,
                    low=9.8 + index * 0.1,
                    close=10.5 + index * 0.1,
                    volume=5_000_000 + index * 100_000,
                )
                for index in range(150)
            ]
        )
    return run_id
