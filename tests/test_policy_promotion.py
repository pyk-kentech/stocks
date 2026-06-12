from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision
import pytest

from stock_risk_mcp.policy_promotion import (
    activate_policy,
    approve_policy,
    create_policy_promotion_proposal,
)
from stock_risk_mcp.repository import RiskRepository
from tests.test_policy_evaluation_suite import _replay
from stock_risk_mcp.policy_evaluation_suite import evaluate_policy_suite
from stock_risk_mcp.strategy_policy import StrategyPolicyStatus, create_default_strategy_policy


def test_repository_round_trips_accepted_promotion_proposal(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    suite = evaluate_policy_suite([(_replay("r1", "base"), _replay("r1", "candidate"))], 1, 1)
    suite = suite.model_copy(update={"recommendation": PolicyEvaluationDecision.ACCEPT})
    proposal = create_policy_promotion_proposal(suite)

    repository.save_policy_promotion_proposal(proposal)

    assert proposal.proposed_status == "APPROVED"
    assert repository.list_policy_promotion_proposals() == [proposal]


def test_approve_and_activate_are_explicit_and_retire_previous_active(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    active = create_default_strategy_policy()
    draft = active.model_copy(update={"version": "v2", "status": StrategyPolicyStatus.DRAFT})
    repository.save_strategy_policy(active)
    repository.save_strategy_policy(draft)

    with pytest.raises(ValueError, match="APPROVED"):
        activate_policy(repository, "default", "v2")
    approve_policy(repository, "default", "v2")
    activated = activate_policy(repository, "default", "v2")

    assert activated.status == StrategyPolicyStatus.ACTIVE
    assert repository.get_strategy_policy("default", "v1").status == StrategyPolicyStatus.RETIRED


def test_rejected_policy_cannot_be_approved(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    rejected = create_default_strategy_policy().model_copy(update={"status": StrategyPolicyStatus.REJECTED})
    repository.save_strategy_policy(rejected)

    with pytest.raises(ValueError, match="REJECTED"):
        approve_policy(repository, "default", "v1")
