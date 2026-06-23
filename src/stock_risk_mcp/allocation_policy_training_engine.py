from __future__ import annotations

from stock_risk_mcp.allocation_policy_training_guard import (
    validate_allocation_policy_training_metadata_safety,
)
from stock_risk_mcp.allocation_policy_training_models import (
    AllocationPolicyArtifactReport,
    AllocationPolicyCandidateInput,
    AllocationPolicyDrawdownStabilityReport,
    AllocationPolicyPromotionDecision,
    AllocationPolicyPromotionReadinessReport,
    AllocationPolicyRiskAdjustedReport,
    AllocationPolicyTrainingGapCategory,
    AllocationPolicyTrainingGapEntry,
    AllocationPolicyTrainingGapReport,
    AllocationPolicyTrainingSafetyReport,
    AllocationPolicyTurnoverSlippageReport,
    AllocationPolicyWalkForwardReport,
    PolicyTrainingSummaryReport,
    RegimeActionSelectionReport,
)


def build_allocation_policy_training_sandbox(
    training_input: AllocationPolicyCandidateInput,
) -> AllocationPolicyCandidateInput:
    gap_entries: list[AllocationPolicyTrainingGapEntry] = []
    for audit in training_input.audit_records:
        validate_allocation_policy_training_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="allocation policy training",
        )

    policy_scores = training_input.training_evaluation_input.policy_scores_by_action
    best_action = max(policy_scores, key=policy_scores.get)
    policy_training_summary_report = PolicyTrainingSummaryReport(
        report_id=f"{training_input.input_id}-POLICY-TRAINING-SUMMARY-REPORT",
        policy_score_deterministic=True,
        trained_action_count=len(policy_scores),
        best_action=best_action,
    )

    action_count = len({action for dist in training_input.training_evaluation_input.selected_action_distribution_by_regime.values() for action in dist})
    regime_action_selection_report = RegimeActionSelectionReport(
        report_id=f"{training_input.input_id}-REGIME-ACTION-SELECTION-REPORT",
        regime_count=len(training_input.training_evaluation_input.selected_action_distribution_by_regime),
        action_count=action_count,
    )

    walk_forward_report = AllocationPolicyWalkForwardReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-WALK-FORWARD-REPORT",
        train_score=training_input.training_evaluation_input.train_score,
        validation_score=training_input.training_evaluation_input.validation_score,
        test_score=training_input.training_evaluation_input.test_score,
        forward_paper_score=training_input.training_evaluation_input.forward_paper_score,
        stable_fold_count=training_input.training_evaluation_input.stable_fold_count,
        fold_count=training_input.training_evaluation_input.fold_count,
    )

    fold_stability_ratio = (
        training_input.training_evaluation_input.stable_fold_count / training_input.training_evaluation_input.fold_count
    )
    unstable_folds = fold_stability_ratio < 0.6
    if unstable_folds:
        gap_entries.append(
            _gap(
                training_input,
                "UNSTABLE-FOLD-PERFORMANCE",
                AllocationPolicyTrainingGapCategory.UNSTABLE_FOLD_PERFORMANCE,
                "BLOCKING",
                "fold performance is unstable",
            )
        )

    risk_adjusted_report = AllocationPolicyRiskAdjustedReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-RISK-ADJUSTED-REPORT",
        risk_adjusted_score=training_input.training_evaluation_input.risk_adjusted_score,
    )

    excessive_turnover_slippage = (
        training_input.training_evaluation_input.turnover_score > 0.30
        or training_input.training_evaluation_input.slippage_score > 0.15
    )
    if excessive_turnover_slippage:
        gap_entries.append(
            _gap(
                training_input,
                "EXCESSIVE-TURNOVER-SLIPPAGE",
                AllocationPolicyTrainingGapCategory.EXCESSIVE_TURNOVER_SLIPPAGE,
                "WARNING",
                "turnover or slippage is too high",
            )
        )
    turnover_slippage_report = AllocationPolicyTurnoverSlippageReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-TURNOVER-SLIPPAGE-REPORT",
        turnover_score=training_input.training_evaluation_input.turnover_score,
        slippage_score=training_input.training_evaluation_input.slippage_score,
        excessive_turnover_slippage=excessive_turnover_slippage,
    )

    excessive_drawdown = training_input.training_evaluation_input.max_drawdown_score > 0.20
    if excessive_drawdown:
        gap_entries.append(
            _gap(
                training_input,
                "EXCESSIVE-DRAWDOWN",
                AllocationPolicyTrainingGapCategory.EXCESSIVE_DRAWDOWN,
                "WARNING",
                "drawdown is too high for paper candidate promotion",
            )
        )
    drawdown_stability_report = AllocationPolicyDrawdownStabilityReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-DRAWDOWN-STABILITY-REPORT",
        max_drawdown_score=training_input.training_evaluation_input.max_drawdown_score,
        fold_stability_ratio=fold_stability_ratio,
        unstable_folds_flagged=unstable_folds,
    )

    if training_input.training_input.learning_dataset_readiness_decision != "TRAINING_READY":
        gap_entries.append(
            _gap(
                training_input,
                "MISSING-V75-TRAINING-READY-DEPENDENCY",
                AllocationPolicyTrainingGapCategory.MISSING_V75_TRAINING_READY_DEPENDENCY,
                "WARNING",
                "v7.5 dataset dependency is not training-ready",
            )
        )
    if training_input.future_outcome_leakage_detected:
        gap_entries.append(
            _gap(
                training_input,
                "INVALID-LEAKY-DATASET",
                AllocationPolicyTrainingGapCategory.INVALID_LEAKY_DATASET,
                "BLOCKING",
                "future outcome leakage detected",
            )
        )
    if training_input.dependency_status.walk_forward_validation_decision is None:
        gap_entries.append(
            _gap(
                training_input,
                "MISSING-WALK-FORWARD-EVIDENCE",
                AllocationPolicyTrainingGapCategory.MISSING_WALK_FORWARD_EVIDENCE,
                "WARNING",
                "walk-forward evidence is missing",
            )
        )
    if training_input.dependency_status.training_promotion_dependency_decision in {"BLOCKED", "REJECTED"}:
        gap_entries.append(
            _gap(
                training_input,
                "BLOCKED-PROMOTION-DEPENDENCY",
                AllocationPolicyTrainingGapCategory.BLOCKED_PROMOTION_DEPENDENCY,
                "BLOCKING",
                "training promotion dependency is blocked",
            )
        )
    if training_input.dependency_status.ensemble_dependency_decision in {"BLOCKED", "REJECTED"}:
        gap_entries.append(
            _gap(
                training_input,
                "BLOCKED-ENSEMBLE-DEPENDENCY",
                AllocationPolicyTrainingGapCategory.BLOCKED_ENSEMBLE_DEPENDENCY,
                "BLOCKING",
                "ensemble dependency is blocked",
            )
        )
    if not training_input.dependency_status.point_in_time_evidence_present:
        gap_entries.append(
            _gap(
                training_input,
                "MISSING-POINT-IN-TIME-EVIDENCE",
                AllocationPolicyTrainingGapCategory.MISSING_POINT_IN_TIME_EVIDENCE,
                "WARNING",
                "point-in-time evidence is missing",
            )
        )
    if not training_input.dependency_status.available_at_evidence_present:
        gap_entries.append(
            _gap(
                training_input,
                "MISSING-AVAILABLE-AT-EVIDENCE",
                AllocationPolicyTrainingGapCategory.MISSING_AVAILABLE_AT_EVIDENCE,
                "WARNING",
                "available_at evidence is missing",
            )
        )
    if not training_input.dependency_status.leakage_evidence_present:
        gap_entries.append(
            _gap(
                training_input,
                "MISSING-LEAKAGE-EVIDENCE",
                AllocationPolicyTrainingGapCategory.MISSING_LEAKAGE_EVIDENCE,
                "WARNING",
                "leakage evidence is missing",
            )
        )

    model_artifact_policy_report = AllocationPolicyArtifactReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-ARTIFACT-REPORT",
        local_only=training_input.policy_candidate.artifact_metadata.local_only,
        offline_only=training_input.policy_candidate.artifact_metadata.offline_only,
        non_production=training_input.policy_candidate.artifact_metadata.non_production,
    )

    safety_report = AllocationPolicyTrainingSafetyReport(
        safety_report_id=f"{training_input.input_id}-SAFETY-REPORT",
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

    decision, reason = _decide(training_input, gap_entries, unstable_folds, excessive_turnover_slippage, excessive_drawdown)
    promotion_report = AllocationPolicyPromotionReadinessReport(
        report_id=f"{training_input.input_id}-ALLOCATION-POLICY-PROMOTION-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    gap_entries.append(
        _gap(
            training_input,
            "SANDBOX-REPORT-GENERATED",
            AllocationPolicyTrainingGapCategory.SANDBOX_REPORT_GENERATED,
            "REPORT_ONLY",
            "offline allocation policy sandbox report generated",
        )
    )
    gap_report = AllocationPolicyTrainingGapReport(
        gap_report_id=f"{training_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for entry in gap_entries if entry.severity == "BLOCKING"),
        warning_gap_count=sum(1 for entry in gap_entries if entry.severity == "WARNING"),
    )

    return training_input.model_copy(
        update={
            "policy_training_summary_report": policy_training_summary_report,
            "regime_action_selection_report": regime_action_selection_report,
            "allocation_policy_walk_forward_report": walk_forward_report,
            "allocation_policy_risk_adjusted_report": risk_adjusted_report,
            "allocation_policy_turnover_slippage_report": turnover_slippage_report,
            "allocation_policy_drawdown_stability_report": drawdown_stability_report,
            "model_artifact_policy_report": model_artifact_policy_report,
            "policy_promotion_readiness_report": promotion_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _decide(training_input, gap_entries, unstable_folds: bool, excessive_turnover_slippage: bool, excessive_drawdown: bool):
    blocking = [entry for entry in gap_entries if entry.severity == "BLOCKING"]
    warnings = [entry for entry in gap_entries if entry.severity == "WARNING"]
    if blocking:
        return AllocationPolicyPromotionDecision.BLOCKED, blocking[0].message
    if training_input.training_input.learning_dataset_readiness_decision != "TRAINING_READY":
        return AllocationPolicyPromotionDecision.GAP, "v7.5 dataset dependency is not training-ready"
    if warnings:
        if excessive_turnover_slippage or excessive_drawdown:
            return AllocationPolicyPromotionDecision.TRAINED_OFFLINE, warnings[0].message
        return AllocationPolicyPromotionDecision.GAP, warnings[0].message
    if unstable_folds:
        return AllocationPolicyPromotionDecision.TRAINED_OFFLINE, "fold stability is insufficient for paper candidate"
    if excessive_turnover_slippage or excessive_drawdown:
        return AllocationPolicyPromotionDecision.TRAINED_OFFLINE, "risk penalties prevent paper candidate promotion"
    if training_input.dependency_status.walk_forward_validation_decision == "PAPER_READY":
        return AllocationPolicyPromotionDecision.PAPER_CANDIDATE, "offline policy passed lightweight training and evaluation gates"
    return AllocationPolicyPromotionDecision.TRAINED_OFFLINE, "offline policy candidate trained and evaluated locally"


def _gap(training_input, suffix, category, severity, message):
    return AllocationPolicyTrainingGapEntry(
        gap_id=f"{training_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
