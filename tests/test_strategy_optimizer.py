from __future__ import annotations

import json

import pytest

from stock_risk_mcp.cli import main
from stock_risk_mcp.strategy_optimizer import StrategyOptimizer
from stock_risk_mcp.strategy_policy import StrategyPolicyStatus, create_default_strategy_policy


def test_optimizer_proposes_deterministic_draft_candidates_with_normalized_weights() -> None:
    baseline = create_default_strategy_policy()
    optimizer = StrategyOptimizer()

    candidates = optimizer.propose_candidate_policies(baseline, 5)

    assert len(candidates) == 5
    assert all(candidate.status == StrategyPolicyStatus.DRAFT for candidate in candidates)
    assert all(sum(candidate.weights.values()) == pytest.approx(1) for candidate in candidates)
    assert all(candidate.parent_policy_id == baseline.policy_id for candidate in candidates)
    assert len({candidate.version for candidate in candidates}) == 5
    assert candidates == optimizer.propose_candidate_policies(baseline, 5)


def test_optimizer_never_auto_activates_candidate() -> None:
    candidate = StrategyOptimizer().perturb_policy(create_default_strategy_policy(), "max_basket_loss_pct_down")

    assert candidate.status == StrategyPolicyStatus.DRAFT
    assert candidate.risk_overrides["max_basket_loss_pct"] == 0.75


def test_optimizer_keeps_versions_unique_when_mutations_repeat() -> None:
    candidates = StrategyOptimizer().propose_candidate_policies(create_default_strategy_policy(), 15)

    assert len({candidate.version for candidate in candidates}) == 15


def test_strategy_cli_initializes_proposes_evaluates_and_lists(tmp_path, capsys) -> None:
    db_path = tmp_path / "risk.sqlite3"

    init_output = _run_cli(capsys, ["strategy-init", "--db", str(db_path)])
    active_output = _run_cli(capsys, ["strategy-active", "--db", str(db_path)])
    propose_output = _run_cli(capsys, ["strategy-propose", "--db", str(db_path), "--n", "3"])
    policies_output = _run_cli(capsys, ["strategy-policies", "--db", str(db_path)])
    evaluate_output = _run_cli(
        capsys,
        [
            "strategy-evaluate",
            "--db",
            str(db_path),
            "--policy-id",
            propose_output["policies"][0]["policy_id"],
            "--version",
            propose_output["policies"][0]["version"],
            "--horizon-days",
            "10",
        ],
    )
    experiments_output = _run_cli(capsys, ["strategy-experiments", "--db", str(db_path)])

    assert init_output["status"] == "ACTIVE"
    assert active_output["status"] == "ACTIVE"
    assert len(propose_output["policies"]) == 3
    assert all(policy["status"] == "DRAFT" for policy in propose_output["policies"])
    assert len(policies_output["policies"]) == 4
    assert evaluate_output["evaluation_mode"] == "COMMON_OUTCOME_EVALUATION"
    assert "not actual candidate policy performance" in evaluate_output["warning"]
    assert experiments_output["experiments"][0]["evaluation_mode"] == "COMMON_OUTCOME_EVALUATION"


def _run_cli(capsys, args: list[str]) -> dict:
    main(args)
    return json.loads(capsys.readouterr().out)
