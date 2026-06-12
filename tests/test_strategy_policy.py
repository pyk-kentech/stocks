from __future__ import annotations

import pytest

from stock_risk_mcp.strategy_policy import (
    StrategyPolicyStatus,
    create_default_strategy_policy,
    normalize_weights,
    validate_strategy_policy,
)
from stock_risk_mcp.repository import RiskRepository


def test_default_strategy_policy_is_active_and_valid() -> None:
    policy = create_default_strategy_policy()

    assert policy.policy_id == "default"
    assert policy.version == "v1"
    assert policy.status == StrategyPolicyStatus.ACTIVE
    assert sum(policy.weights.values()) == pytest.approx(1)
    assert validate_strategy_policy(policy) == policy


def test_normalize_weights_makes_sum_one() -> None:
    normalized = normalize_weights({"a": 2, "b": 1})

    assert normalized == pytest.approx({"a": 2 / 3, "b": 1 / 3})
    assert sum(normalized.values()) == pytest.approx(1)


def test_strategy_policy_rejects_invalid_weights_thresholds_and_hard_risk_keys() -> None:
    baseline = create_default_strategy_policy()

    with pytest.raises(ValueError, match="weights sum"):
        validate_strategy_policy(baseline.model_copy(update={"weights": {"a": 0.5}}))
    with pytest.raises(ValueError, match="non-negative"):
        validate_strategy_policy(baseline.model_copy(update={"weights": {"a": 1.1, "b": -0.1}}))
    with pytest.raises(ValueError, match="A > B > C"):
        validate_strategy_policy(
            baseline.model_copy(update={"setup_thresholds": {"A": 60, "B": 80, "C": 40, "NO_TRADE": 0}})
        )
    with pytest.raises(ValueError, match="forbidden hard risk"):
        validate_strategy_policy(
            baseline.model_copy(update={"risk_overrides": {**baseline.risk_overrides, "allow_margin": True}})
        )


def test_strategy_policy_rejects_out_of_range_loss_overrides() -> None:
    baseline = create_default_strategy_policy()

    with pytest.raises(ValueError, match="max_basket_loss_pct"):
        validate_strategy_policy(
            baseline.model_copy(update={"risk_overrides": {**baseline.risk_overrides, "max_basket_loss_pct": 5.1}})
        )
    with pytest.raises(ValueError, match="max_single_candidate_loss_pct"):
        validate_strategy_policy(
            baseline.model_copy(
                update={"risk_overrides": {**baseline.risk_overrides, "max_single_candidate_loss_pct": 0}}
            )
        )


def test_repository_saves_lists_and_updates_strategy_policies(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    policy = create_default_strategy_policy()

    assert repository.save_strategy_policy(policy) == 1
    assert repository.get_strategy_policy("default", "v1") == policy
    assert repository.get_active_strategy_policy() == policy
    assert repository.list_strategy_policies() == [policy]

    repository.update_strategy_policy_status("default", "v1", "RETIRED")

    assert repository.get_active_strategy_policy() is None
    assert repository.get_strategy_policy("default", "v1").status == StrategyPolicyStatus.RETIRED
