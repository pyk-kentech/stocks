import json
from datetime import date, datetime

from stock_risk_mcp.cli import main
from stock_risk_mcp.policy_replay_result import PolicyReplayMode, PolicyReplayResult, PolicyReplayStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.strategy_policy import StrategyPolicyStatus, create_default_strategy_policy


def test_policy_evaluation_and_promotion_cli_commands(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    repository = RiskRepository(db)
    active = create_default_strategy_policy()
    draft = active.model_copy(update={"version": "v2", "status": StrategyPolicyStatus.DRAFT})
    repository.save_strategy_policy(active)
    repository.save_strategy_policy(draft)
    for index in range(5):
        repository.save_policy_replay_result(_result(f"r{index}", "v1", 50, 1))
        repository.save_policy_replay_result(_result(f"r{index}", "v2", 56, 3))
    args = [
        "--db", str(db), "--baseline-policy-id", "default", "--baseline-policy-version", "v1",
        "--candidate-policy-id", "default", "--candidate-policy-version", "v2",
        "--horizon-days", "10", "--account-equity", "10000", "--cash-available", "5000",
    ]
    for index in range(5):
        args += ["--replay-run-id", f"r{index}"]

    main(["policy-evaluate-suite", *args])
    suite = json.loads(capsys.readouterr().out)
    main(["policy-propose-promotion", "--db", str(db), "--suite-id", suite["suite_id"]])
    proposal = json.loads(capsys.readouterr().out)
    main(["policy-evaluation-suites", "--db", str(db)])
    suites = json.loads(capsys.readouterr().out)
    main(["policy-promotion-proposals", "--db", str(db)])
    proposals = json.loads(capsys.readouterr().out)
    main(["policy-approve", "--db", str(db), "--policy-id", "default", "--policy-version", "v2"])
    approved = json.loads(capsys.readouterr().out)
    main(["policy-activate", "--db", str(db), "--policy-id", "default", "--policy-version", "v2"])
    activated = json.loads(capsys.readouterr().out)

    assert suite["completed_pair_count"] == 5
    assert proposal["proposed_status"] == "APPROVED"
    assert suites["suites"][0]["suite_id"] == suite["suite_id"]
    assert proposals["proposals"][0]["proposal_id"] == proposal["proposal_id"]
    assert approved["status"] == "APPROVED"
    assert activated["status"] == "ACTIVE"


def _result(run_id, version, objective, return_pct):
    return PolicyReplayResult(
        policy_replay_id=f"{run_id}-{version}", source_replay_run_id=run_id,
        replay_mode=PolicyReplayMode.FULL_POLICY_REPLAY, policy_id="default", policy_version=version,
        as_of_date=date(2026, 1, 1), horizon_days=10, candidate_count=3, trade_plan_count=3,
        realized_return_pct=return_pct, objective_score=objective, win_count=2, loss_count=1,
        no_data_count=0, status=PolicyReplayStatus.COMPLETED, notes=[], created_at=datetime(2026, 1, 2),
    )
