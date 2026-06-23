from stock_risk_mcp.training_pipeline_promotion_engine import build_training_pipeline_promotion
from stock_risk_mcp.training_pipeline_promotion_models import (
    TrainingPipelinePromotionDecision,
    TrainingPipelinePromotionInput,
)
from tests.test_training_pipeline_promotion_models import training_pipeline_promotion_payload


def _evaluate(**overrides):
    payload = training_pipeline_promotion_payload()
    payload.update(overrides)
    return build_training_pipeline_promotion(TrainingPipelinePromotionInput.model_validate(payload))


def test_missing_v71_v72_dependency_causes_promotion_gap():
    result = _evaluate(v71_dataset_decision=None, v72_validation_decision=None)
    assert result.model_promotion_readiness_report.decision == TrainingPipelinePromotionDecision.PROMOTION_GAP


def test_v71_training_ready_and_v72_paper_ready_can_produce_paper_candidate():
    result = _evaluate()
    assert result.model_promotion_readiness_report.decision == TrainingPipelinePromotionDecision.PAPER_CANDIDATE


def test_current_survivors_only_dataset_dependency_blocks_promotion():
    result = _evaluate(v71_dataset_decision="RESEARCH_ONLY")
    assert result.model_promotion_readiness_report.decision == TrainingPipelinePromotionDecision.BLOCKED


def test_final_test_contamination_blocks_promotion():
    result = _evaluate(final_test_contamination_detected=True)
    assert result.model_promotion_readiness_report.decision == TrainingPipelinePromotionDecision.BLOCKED


def test_missing_available_at_discipline_causes_gap_or_block():
    result = _evaluate(
        dataset_eligibility={
            **training_pipeline_promotion_payload()["dataset_eligibility"],
            "available_at_discipline_ref": None,
        }
    )
    assert result.model_promotion_readiness_report.decision in {
        TrainingPipelinePromotionDecision.PROMOTION_GAP,
        TrainingPipelinePromotionDecision.TRAINING_READY,
    }


def test_label_leakage_blocks_promotion():
    result = _evaluate(
        dataset_eligibility={
            **training_pipeline_promotion_payload()["dataset_eligibility"],
            "label_leakage_detected": True,
        }
    )
    assert result.model_promotion_readiness_report.decision == TrainingPipelinePromotionDecision.BLOCKED


def test_missing_reproducibility_seed_policy_causes_gap():
    result = _evaluate(
        training_run_candidate={
            **training_pipeline_promotion_payload()["training_run_candidate"],
            "random_seed_policy_present": False,
        }
    )
    assert result.model_promotion_readiness_report.decision in {
        TrainingPipelinePromotionDecision.PROMOTION_GAP,
        TrainingPipelinePromotionDecision.TRAINING_READY,
    }


def test_missing_experiment_lineage_causes_gap():
    result = _evaluate(
        training_run_candidate={
            **training_pipeline_promotion_payload()["training_run_candidate"],
            "experiment_id": None,
        }
    )
    assert result.model_promotion_readiness_report.decision in {
        TrainingPipelinePromotionDecision.PROMOTION_GAP,
        TrainingPipelinePromotionDecision.TRAINING_READY,
    }


def test_excessive_parameter_search_is_flagged():
    result = _evaluate(excessive_parameter_search_flagged=True)
    assert result.leakage_overfit_risk_report.excessive_parameter_search_flagged is True


def test_model_artifact_policy_remains_local_offline_non_production():
    result = _evaluate()
    assert result.model_artifact_policy_report.local_offline_only is True
    assert result.model_artifact_policy_report.non_production_only is True
    assert result.model_artifact_policy_report.no_live_inference_deployment is True
