from stock_risk_mcp.allocation_policy_training_engine import build_allocation_policy_training_sandbox
from stock_risk_mcp.allocation_policy_training_models import (
    AllocationPolicyCandidateInput,
    AllocationPolicyPromotionDecision,
)
from tests.test_allocation_policy_training_models import allocation_policy_training_payload


def _evaluate(**overrides):
    payload = allocation_policy_training_payload()
    payload.update(overrides)
    return build_allocation_policy_training_sandbox(AllocationPolicyCandidateInput.model_validate(payload))


def test_missing_v75_training_ready_dependency_causes_gap():
    result = _evaluate(
        training_input={
            **allocation_policy_training_payload()["training_input"],
            "learning_dataset_readiness_decision": "GAP",
        }
    )
    assert result.policy_promotion_readiness_report.decision == AllocationPolicyPromotionDecision.GAP


def test_invalid_leaky_dataset_blocks_promotion():
    result = _evaluate(future_outcome_leakage_detected=True)
    assert result.policy_promotion_readiness_report.decision == AllocationPolicyPromotionDecision.BLOCKED


def test_deterministic_lightweight_training_produces_stable_policy_scores():
    result = _evaluate()
    assert result.policy_training_summary_report.policy_score_deterministic is True


def test_policy_action_distribution_by_regime_is_reported():
    result = _evaluate()
    assert result.regime_action_selection_report.regime_count == 2


def test_walk_forward_evaluation_summary_is_required():
    result = _evaluate(
        dependency_status={
            **allocation_policy_training_payload()["dependency_status"],
            "walk_forward_validation_decision": None,
        }
    )
    assert result.policy_promotion_readiness_report.decision == AllocationPolicyPromotionDecision.GAP


def test_unstable_folds_block_paper_candidate():
    result = _evaluate(
        training_evaluation_input={
            **allocation_policy_training_payload()["training_evaluation_input"],
            "stable_fold_count": 1,
            "fold_count": 4,
        }
    )
    assert result.policy_promotion_readiness_report.decision != AllocationPolicyPromotionDecision.PAPER_CANDIDATE


def test_excessive_turnover_slippage_blocks_or_downgrades():
    result = _evaluate(
        training_evaluation_input={
            **allocation_policy_training_payload()["training_evaluation_input"],
            "turnover_score": 0.45,
            "slippage_score": 0.22,
        }
    )
    assert result.policy_promotion_readiness_report.decision in {
        AllocationPolicyPromotionDecision.BLOCKED,
        AllocationPolicyPromotionDecision.TRAINED_OFFLINE,
    }


def test_excessive_drawdown_blocks_or_downgrades():
    result = _evaluate(
        training_evaluation_input={
            **allocation_policy_training_payload()["training_evaluation_input"],
            "max_drawdown_score": 0.30,
        }
    )
    assert result.policy_promotion_readiness_report.decision in {
        AllocationPolicyPromotionDecision.BLOCKED,
        AllocationPolicyPromotionDecision.TRAINED_OFFLINE,
    }


def test_valid_fixture_can_become_trained_offline():
    result = _evaluate(
        dependency_status={
            **allocation_policy_training_payload()["dependency_status"],
            "walk_forward_validation_decision": "VALIDATION_READY",
        }
    )
    assert result.policy_promotion_readiness_report.decision in {
        AllocationPolicyPromotionDecision.TRAINED_OFFLINE,
        AllocationPolicyPromotionDecision.PAPER_CANDIDATE,
    }


def test_strong_valid_fixture_can_become_paper_candidate():
    result = _evaluate()
    assert result.policy_promotion_readiness_report.decision == AllocationPolicyPromotionDecision.PAPER_CANDIDATE


def test_artifact_policy_remains_local_offline_non_production():
    result = _evaluate()
    assert result.model_artifact_policy_report.local_only is True
    assert result.model_artifact_policy_report.offline_only is True
    assert result.model_artifact_policy_report.non_production is True
