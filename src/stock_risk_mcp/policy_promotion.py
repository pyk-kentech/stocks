from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationDecision, PolicyEvaluationSuiteResult
from stock_risk_mcp.strategy_policy import StrategyPolicyStatus


class PolicyPromotionProposal(StrictModel):
    proposal_id: str
    suite_id: str
    candidate_policy_id: str
    candidate_policy_version: str
    from_status: str
    proposed_status: str
    recommendation: PolicyEvaluationDecision
    reason: str
    created_at: datetime


def create_policy_promotion_proposal(suite: PolicyEvaluationSuiteResult, from_status: str = "DRAFT") -> PolicyPromotionProposal:
    proposed = {
        PolicyEvaluationDecision.ACCEPT: "APPROVED",
        PolicyEvaluationDecision.REJECT: "REJECTED",
        PolicyEvaluationDecision.NEED_MORE_DATA: "DRAFT",
    }[suite.recommendation]
    return PolicyPromotionProposal(
        proposal_id=uuid4().hex, suite_id=suite.suite_id, candidate_policy_id=suite.candidate_policy_id,
        candidate_policy_version=suite.candidate_policy_version, from_status=from_status, proposed_status=proposed,
        recommendation=suite.recommendation, reason=f"Suite recommendation: {suite.recommendation.value}",
        created_at=datetime.now(),
    )


def approve_policy(repository, policy_id: str, version: str):
    policy = repository.get_strategy_policy(policy_id, version)
    if policy.status == StrategyPolicyStatus.REJECTED:
        raise ValueError("REJECTED policy cannot be approved")
    repository.update_strategy_policy_status(policy_id, version, StrategyPolicyStatus.APPROVED.value)
    return repository.get_strategy_policy(policy_id, version)


def activate_policy(repository, policy_id: str, version: str):
    policy = repository.get_strategy_policy(policy_id, version)
    if policy.status != StrategyPolicyStatus.APPROVED:
        raise ValueError("Only APPROVED policy can be activated")
    for active in repository.list_strategy_policies(limit=1_000_000):
        if active.status == StrategyPolicyStatus.ACTIVE:
            repository.update_strategy_policy_status(active.policy_id, active.version, StrategyPolicyStatus.RETIRED.value)
    repository.update_strategy_policy_status(policy_id, version, StrategyPolicyStatus.ACTIVE.value)
    return repository.get_strategy_policy(policy_id, version)
