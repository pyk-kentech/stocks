from __future__ import annotations

from stock_risk_mcp.training_pipeline_promotion_guard import (
    validate_training_pipeline_promotion_metadata_safety,
)
from stock_risk_mcp.training_pipeline_promotion_models import (
    LeakageOverfitRiskReport,
    ModelArtifactPolicyReport,
    ModelPromotionReadinessReport,
    ReproducibilityReport,
    TrainingDependencyReport,
    TrainingEligibilityReport,
    TrainingPipelinePromotionDecision,
    TrainingPipelinePromotionGapCategory,
    TrainingPipelinePromotionGapEntry,
    TrainingPipelinePromotionGapReport,
    TrainingPipelinePromotionInput,
    TrainingPipelinePromotionSafetyReport,
)


def build_training_pipeline_promotion(
    promotion_input: TrainingPipelinePromotionInput,
) -> TrainingPipelinePromotionInput:
    gap_entries: list[TrainingPipelinePromotionGapEntry] = []
    for audit in promotion_input.audit_records:
        validate_training_pipeline_promotion_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="training pipeline promotion",
        )

    dependency_complete = all(
        (
            promotion_input.v71_dataset_decision is not None,
            promotion_input.v72_validation_decision is not None,
            promotion_input.v70_robustness_decision is not None,
        )
    )
    dependency_report = TrainingDependencyReport(
        report_id=f"{promotion_input.input_id}-DEPENDENCY-REPORT",
        v71_dataset_decision=promotion_input.v71_dataset_decision,
        v72_validation_decision=promotion_input.v72_validation_decision,
        v70_robustness_decision=promotion_input.v70_robustness_decision,
        dependency_complete=dependency_complete,
    )

    if promotion_input.v71_dataset_decision is None:
        gap_entries.append(_gap(promotion_input, "MISSING-V71-DEPENDENCY", TrainingPipelinePromotionGapCategory.MISSING_V71_DEPENDENCY, "WARNING", "missing v7.1 dependency"))
    elif promotion_input.v71_dataset_decision != "TRAINING_READY":
        gap_entries.append(_gap(promotion_input, "DATASET-NOT-TRAINING-READY", TrainingPipelinePromotionGapCategory.DATASET_NOT_TRAINING_READY, "BLOCKING", "dataset dependency is not training ready"))
    if promotion_input.v72_validation_decision is None:
        gap_entries.append(_gap(promotion_input, "MISSING-V72-DEPENDENCY", TrainingPipelinePromotionGapCategory.MISSING_V72_DEPENDENCY, "WARNING", "missing v7.2 dependency"))
    elif promotion_input.v72_validation_decision not in {"VALIDATION_READY", "PAPER_READY"}:
        gap_entries.append(_gap(promotion_input, "VALIDATION-NOT-READY", TrainingPipelinePromotionGapCategory.VALIDATION_NOT_READY, "BLOCKING", "validation dependency is not ready"))
    if promotion_input.v70_robustness_decision is None:
        gap_entries.append(_gap(promotion_input, "MISSING-V70-DEPENDENCY", TrainingPipelinePromotionGapCategory.MISSING_V70_DEPENDENCY, "WARNING", "missing v7.0 dependency"))
    elif promotion_input.v70_robustness_decision in {"BLOCKED", "REJECTED"}:
        gap_entries.append(_gap(promotion_input, "ROBUSTNESS-BLOCKED", TrainingPipelinePromotionGapCategory.ROBUSTNESS_BLOCKED, "BLOCKING", "robustness dependency is blocked"))

    training_eligibility_report = TrainingEligibilityReport(
        report_id=f"{promotion_input.input_id}-TRAINING-ELIGIBILITY-REPORT",
        dataset_training_eligible=promotion_input.v71_dataset_decision == "TRAINING_READY",
        available_at_discipline_present=bool(promotion_input.dataset_eligibility.available_at_discipline_ref),
        leakage_audit_present=bool(promotion_input.dataset_eligibility.leakage_audit_ref),
        label_leakage_detected=promotion_input.dataset_eligibility.label_leakage_detected,
    )
    if not promotion_input.dataset_eligibility.available_at_discipline_ref:
        gap_entries.append(_gap(promotion_input, "AVAILABLE-AT-DISCIPLINE-MISSING", TrainingPipelinePromotionGapCategory.AVAILABLE_AT_DISCIPLINE_MISSING, "WARNING", "available_at discipline reference missing"))
    if promotion_input.dataset_eligibility.label_leakage_detected or promotion_input.leakage_detected:
        gap_entries.append(_gap(promotion_input, "LABEL-LEAKAGE-DETECTED", TrainingPipelinePromotionGapCategory.LABEL_LEAKAGE_DETECTED, "BLOCKING", "label leakage detected"))

    leakage_overfit_risk_report = LeakageOverfitRiskReport(
        report_id=f"{promotion_input.input_id}-LEAKAGE-OVERFIT-RISK-REPORT",
        leakage_detected=promotion_input.leakage_detected or promotion_input.dataset_eligibility.label_leakage_detected,
        snooping_detected=promotion_input.snooping_detected,
        final_test_contamination_detected=promotion_input.final_test_contamination_detected,
        excessive_parameter_search_flagged=promotion_input.excessive_parameter_search_flagged,
    )
    if promotion_input.snooping_detected:
        gap_entries.append(_gap(promotion_input, "SNOOPING-DETECTED", TrainingPipelinePromotionGapCategory.SNOOPING_DETECTED, "BLOCKING", "data snooping detected"))
    if promotion_input.final_test_contamination_detected:
        gap_entries.append(_gap(promotion_input, "FINAL-TEST-CONTAMINATION-DETECTED", TrainingPipelinePromotionGapCategory.FINAL_TEST_CONTAMINATION_DETECTED, "BLOCKING", "final test contamination detected"))
    if promotion_input.excessive_parameter_search_flagged:
        gap_entries.append(_gap(promotion_input, "EXCESSIVE-PARAMETER-SEARCH", TrainingPipelinePromotionGapCategory.EXCESSIVE_PARAMETER_SEARCH, "WARNING", "excessive parameter search flagged"))

    reproducibility_report = ReproducibilityReport(
        report_id=f"{promotion_input.input_id}-REPRODUCIBILITY-REPORT",
        random_seed_policy_present=promotion_input.training_run_candidate.random_seed_policy_present,
        reproducibility_hash_present=promotion_input.training_run_candidate.reproducibility_hash is not None,
        experiment_lineage_present=promotion_input.training_run_candidate.experiment_id is not None,
    )
    if not promotion_input.training_run_candidate.random_seed_policy_present:
        gap_entries.append(_gap(promotion_input, "REPRODUCIBLE-SEED-POLICY-MISSING", TrainingPipelinePromotionGapCategory.REPRODUCIBLE_SEED_POLICY_MISSING, "WARNING", "reproducible seed policy missing"))
    if promotion_input.training_run_candidate.experiment_id is None:
        gap_entries.append(_gap(promotion_input, "EXPERIMENT-LINEAGE-MISSING", TrainingPipelinePromotionGapCategory.EXPERIMENT_LINEAGE_MISSING, "WARNING", "experiment lineage missing"))

    metadata_reproducible = all(
        (
            promotion_input.training_run_candidate.random_seed_policy_present,
            promotion_input.training_run_candidate.reproducibility_hash is not None,
            promotion_input.training_run_candidate.experiment_id is not None,
        )
    )
    artifact_policy_report = ModelArtifactPolicyReport(
        report_id=f"{promotion_input.input_id}-MODEL-ARTIFACT-POLICY-REPORT",
        local_offline_only=True,
        non_production_only=True,
        no_live_inference_deployment=True,
        no_order_connection=True,
        no_account_connection=True,
        metadata_reproducible=metadata_reproducible and promotion_input.model_artifact_metadata_reproducible,
    )
    if not artifact_policy_report.metadata_reproducible:
        gap_entries.append(_gap(promotion_input, "ARTIFACT-POLICY-INVALID", TrainingPipelinePromotionGapCategory.ARTIFACT_POLICY_INVALID, "WARNING", "artifact metadata is insufficient for reproducibility"))

    safety_report = TrainingPipelinePromotionSafetyReport(
        safety_report_id=f"{promotion_input.input_id}-SAFETY-REPORT",
        blocked_capabilities=[
            "LIVE_TRADING_BLOCKED",
            "REAL_ORDER_BLOCKED",
            "ACCOUNT_MUTATION_BLOCKED",
            "BROKER_API_BLOCKED",
            "NETWORK_BLOCKED",
            "AUTONOMOUS_TRADING_BLOCKED",
        ],
        findings=["local_offline_report_only=true"],
    )

    decision, reason = _decide(promotion_input, gap_entries)
    promotion_report = ModelPromotionReadinessReport(
        report_id=f"{promotion_input.input_id}-MODEL-PROMOTION-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    gap_entries.append(_gap(promotion_input, "TRAINING-PROMOTION-REPORT-GENERATED", TrainingPipelinePromotionGapCategory.TRAINING_PROMOTION_REPORT_GENERATED, "REPORT_ONLY", "training pipeline promotion report generated"))
    gap_report = TrainingPipelinePromotionGapReport(
        gap_report_id=f"{promotion_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
    )
    return promotion_input.model_copy(
        update={
            "training_eligibility_report": training_eligibility_report,
            "dependency_report": dependency_report,
            "leakage_overfit_risk_report": leakage_overfit_risk_report,
            "reproducibility_report": reproducibility_report,
            "model_artifact_policy_report": artifact_policy_report,
            "model_promotion_readiness_report": promotion_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _decide(promotion_input: TrainingPipelinePromotionInput, gap_entries: list[TrainingPipelinePromotionGapEntry]):
    blocking = [entry for entry in gap_entries if entry.severity == "BLOCKING"]
    warnings = [entry for entry in gap_entries if entry.severity == "WARNING"]
    if blocking:
        return TrainingPipelinePromotionDecision.BLOCKED, blocking[0].message
    dependency_complete = all(
        (
            promotion_input.v71_dataset_decision is not None,
            promotion_input.v72_validation_decision is not None,
            promotion_input.v70_robustness_decision is not None,
        )
    )
    if not dependency_complete:
        return TrainingPipelinePromotionDecision.PROMOTION_GAP, "required dependency evidence is missing"
    if warnings:
        if promotion_input.v72_validation_decision == "PAPER_READY" and promotion_input.v71_dataset_decision == "TRAINING_READY":
            return TrainingPipelinePromotionDecision.TRAINING_READY, warnings[0].message
        return TrainingPipelinePromotionDecision.PROMOTION_GAP, warnings[0].message
    if promotion_input.v71_dataset_decision == "TRAINING_READY" and promotion_input.v72_validation_decision == "PAPER_READY":
        return TrainingPipelinePromotionDecision.PAPER_CANDIDATE, "dataset and validation dependencies support paper candidate evaluation"
    if promotion_input.v71_dataset_decision == "TRAINING_READY" and promotion_input.v72_validation_decision == "VALIDATION_READY":
        return TrainingPipelinePromotionDecision.TRAINING_READY, "controlled offline training is allowed"
    return TrainingPipelinePromotionDecision.RESEARCH_ONLY, "exploratory model only"


def _gap(promotion_input, suffix, category, severity, message):
    return TrainingPipelinePromotionGapEntry(
        gap_id=f"{promotion_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
