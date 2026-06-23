from stock_risk_mcp.regime_allocation_learning_engine import build_regime_allocation_learning_dataset
from stock_risk_mcp.regime_allocation_learning_models import (
    LearningDatasetReadinessDecision,
    RegimeAllocationLearningInput,
)
from tests.test_regime_allocation_learning_models import regime_allocation_learning_payload


def _evaluate(**overrides):
    payload = regime_allocation_learning_payload()
    payload.update(overrides)
    return build_regime_allocation_learning_dataset(RegimeAllocationLearningInput.model_validate(payload))


def test_risk_off_regime_does_not_automatically_block():
    result = _evaluate(
        regime_feature_snapshot={
            **regime_allocation_learning_payload()["regime_feature_snapshot"],
            "risk_state": "RISK_OFF",
        }
    )
    assert result.action_candidate_report.action_candidate_count >= 1
    assert result.learning_dataset_readiness_report.decision in {
        LearningDatasetReadinessDecision.RESEARCH_READY,
        LearningDatasetReadinessDecision.TRAINING_READY,
    }


def test_inverse_candidate_requires_full_policy_evidence():
    inverse = {
        **regime_allocation_learning_payload()["action_candidates"][2],
        "liquidity_evidence_ref": None,
    }
    result = _evaluate(
        action_candidates=[
            regime_allocation_learning_payload()["action_candidates"][0],
            regime_allocation_learning_payload()["action_candidates"][1],
            inverse,
        ]
    )
    assert result.learning_dataset_readiness_report.decision == LearningDatasetReadinessDecision.BLOCKED


def test_hedge_inverse_candidate_remains_report_only_and_never_executable():
    result = _evaluate()
    assert result.hedge_inverse_eligibility_report.report_only is True
    assert result.hedge_inverse_eligibility_report.non_executable is True


def test_missing_available_at_causes_gap_or_block():
    result = _evaluate(
        regime_feature_snapshot={
            **regime_allocation_learning_payload()["regime_feature_snapshot"],
            "available_at": None,
        }
    )
    assert result.learning_dataset_readiness_report.decision in {
        LearningDatasetReadinessDecision.GAP,
        LearningDatasetReadinessDecision.BLOCKED,
    }


def test_future_regime_event_leakage_is_blocked():
    result = _evaluate(regime_event_leakage_detected=True)
    assert result.learning_dataset_readiness_report.decision == LearningDatasetReadinessDecision.BLOCKED


def test_future_outcome_leakage_is_blocked():
    result = _evaluate(future_outcome_leakage_detected=True)
    assert result.learning_dataset_readiness_report.decision == LearningDatasetReadinessDecision.BLOCKED


def test_current_survivors_only_dependency_blocks_training_ready():
    result = _evaluate(
        dependency_status={
            **regime_allocation_learning_payload()["dependency_status"],
            "current_survivors_only_dependency": True,
        }
    )
    assert result.learning_dataset_readiness_report.decision == LearningDatasetReadinessDecision.BLOCKED


def test_valid_dataset_can_become_training_ready():
    result = _evaluate()
    assert result.learning_dataset_readiness_report.decision == LearningDatasetReadinessDecision.TRAINING_READY


def test_reward_scoring_includes_penalties():
    result = _evaluate()
    scoring = result.allocation_reward_scoring_report
    assert scoring.max_drawdown_penalty == 0.10
    assert scoring.turnover_penalty == 0.05
    assert scoring.volatility_penalty == 0.04
    assert scoring.benchmark_relative_performance == 0.03
    assert scoring.tail_risk_penalty == 0.02


def test_max_allocation_multipliers_are_bounded():
    result = _evaluate()
    assert result.action_candidate_report.max_allocation_multiplier_capped is True
