from stock_risk_mcp.walk_forward_validation_engine import build_walk_forward_validation
from stock_risk_mcp.walk_forward_validation_models import (
    WalkForwardValidationDecision,
    WalkForwardValidationInput,
)
from tests.test_walk_forward_validation_models import walk_forward_validation_payload


def _evaluate(**overrides):
    payload = walk_forward_validation_payload()
    payload.update(overrides)
    return build_walk_forward_validation(WalkForwardValidationInput.model_validate(payload))


def test_clean_walk_forward_split_can_become_validation_ready_or_paper_ready():
    result = _evaluate()
    assert result.promotion_readiness_report.decision in {
        WalkForwardValidationDecision.VALIDATION_READY,
        WalkForwardValidationDecision.PAPER_READY,
    }


def test_overlapping_train_test_windows_are_blocked():
    result = _evaluate(
        split={
            **walk_forward_validation_payload()["split"],
            "test_window": {
                "start_at": "2024-06-15T00:00:00+09:00",
                "end_at": "2024-12-31T00:00:00+09:00",
            },
        }
    )
    assert result.promotion_readiness_report.decision == WalkForwardValidationDecision.BLOCKED


def test_final_test_repeated_tuning_is_blocked_or_downgraded():
    result = _evaluate(
        experiment_lineage={
            **walk_forward_validation_payload()["experiment_lineage"],
            "final_test_access_count": 3,
        }
    )
    assert result.promotion_readiness_report.decision == WalkForwardValidationDecision.BLOCKED


def test_excessive_parameter_search_is_flagged():
    result = _evaluate(parameter_search_count=99)
    assert result.data_snooping_report.excessive_parameter_search_flagged is True


def test_unregistered_parameter_mutation_is_flagged():
    result = _evaluate(
        experiment_lineage={
            **walk_forward_validation_payload()["experiment_lineage"],
            "unregistered_parameter_mutation_detected": True,
        }
    )
    assert result.data_snooping_report.unregistered_parameter_mutation_flagged is True


def test_single_period_only_success_causes_gap_or_blocked():
    result = _evaluate(
        stability_evidence={
            **walk_forward_validation_payload()["stability_evidence"],
            "single_period_only_success": True,
            "stable_fold_count": 1,
        }
    )
    assert result.promotion_readiness_report.decision in {
        WalkForwardValidationDecision.GAP,
        WalkForwardValidationDecision.BLOCKED,
    }


def test_multiple_stable_folds_can_pass():
    result = _evaluate()
    assert result.stability_report.multiple_stable_folds_present is True


def test_missing_experiment_lineage_causes_gap():
    result = _evaluate(experiment_lineage=None)
    assert result.promotion_readiness_report.decision == WalkForwardValidationDecision.GAP


def test_missing_forward_paper_window_causes_gap_for_paper_ready():
    result = _evaluate(
        split={
            **walk_forward_validation_payload()["split"],
            "forward_paper_window": None,
        }
    )
    assert result.promotion_readiness_report.decision == WalkForwardValidationDecision.GAP


def test_final_test_contamination_report_detects_repeated_access():
    result = _evaluate(
        experiment_lineage={
            **walk_forward_validation_payload()["experiment_lineage"],
            "final_test_access_count": 2,
        }
    )
    assert result.final_test_contamination_report.final_test_contamination_detected is True
