from __future__ import annotations

from stock_risk_mcp.regime_allocation_learning_guard import (
    validate_regime_allocation_learning_metadata_safety,
)
from stock_risk_mcp.regime_allocation_learning_models import (
    ActionCandidateReport,
    AllocationActionType,
    AllocationRewardScoringReport,
    ForwardOutcomeLabelReport,
    HedgeInverseEligibilityReport,
    LearningDatasetReadinessDecision,
    LearningDatasetReadinessReport,
    RegimeAllocationLearningGapCategory,
    RegimeAllocationLearningGapEntry,
    RegimeAllocationLearningGapReport,
    RegimeAllocationLearningInput,
    RegimeAllocationLearningSafetyReport,
    RegimeAllocationLeakageReport,
    RegimeFeatureReport,
)


def build_regime_allocation_learning_dataset(
    learning_input: RegimeAllocationLearningInput,
) -> RegimeAllocationLearningInput:
    gap_entries: list[RegimeAllocationLearningGapEntry] = []
    for audit in learning_input.audit_records:
        validate_regime_allocation_learning_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="regime allocation learning",
        )

    regime_feature_report = RegimeFeatureReport(
        report_id=f"{learning_input.input_id}-REGIME-FEATURE-REPORT",
        available_at_present=learning_input.regime_feature_snapshot.available_at is not None,
        risk_state=learning_input.regime_feature_snapshot.risk_state,
    )
    if learning_input.regime_feature_snapshot.available_at is None:
        gap_entries.append(
            _gap(
                learning_input,
                "MISSING-AVAILABLE-AT",
                RegimeAllocationLearningGapCategory.MISSING_AVAILABLE_AT,
                "WARNING",
                "regime feature snapshot missing available_at",
            )
        )

    inverse_or_hedge_candidates = [
        candidate
        for candidate in learning_input.action_candidates
        if candidate.action_type in {AllocationActionType.INDEX_HEDGE, AllocationActionType.INVERSE_CANDIDATE}
    ]
    max_multiplier_ok = all(candidate.max_allocation_multiplier <= 1.0 for candidate in learning_input.action_candidates)
    action_candidate_report = ActionCandidateReport(
        report_id=f"{learning_input.input_id}-ACTION-CANDIDATE-REPORT",
        action_candidate_count=len(learning_input.action_candidates),
        inverse_or_hedge_candidate_count=len(inverse_or_hedge_candidates),
        max_allocation_multiplier_capped=max_multiplier_ok,
    )
    if not max_multiplier_ok:
        gap_entries.append(
            _gap(
                learning_input,
                "MAX-ALLOCATION-MULTIPLIER-EXCEEDED",
                RegimeAllocationLearningGapCategory.MAX_ALLOCATION_MULTIPLIER_EXCEEDED,
                "BLOCKING",
                "action candidate allocation multiplier exceeds safe bound",
            )
        )

    inverse_policy_complete = all(
        all(
            (
                candidate.instrument_eligibility_ref,
                candidate.liquidity_evidence_ref,
                candidate.eligibility_ref,
                candidate.leverage_flag,
                candidate.daily_reset_warning,
                candidate.max_allocation_cap is not None,
                candidate.short_holding_period_warning,
                candidate.tracking_error_basis_risk_note,
                candidate.no_execution,
            )
        )
        for candidate in inverse_or_hedge_candidates
    )
    if inverse_or_hedge_candidates and not inverse_policy_complete:
        gap_entries.append(
            _gap(
                learning_input,
                "INVERSE-POLICY-EVIDENCE-MISSING",
                RegimeAllocationLearningGapCategory.INVERSE_POLICY_EVIDENCE_MISSING,
                "BLOCKING",
                "inverse or hedge candidate is missing required evidence",
            )
        )
    if any(not candidate.no_execution for candidate in inverse_or_hedge_candidates):
        gap_entries.append(
            _gap(
                learning_input,
                "HEDGE-INVERSE-EXECUTION-FLAG-DETECTED",
                RegimeAllocationLearningGapCategory.HEDGE_INVERSE_EXECUTION_FLAG_DETECTED,
                "BLOCKING",
                "hedge or inverse candidate cannot become executable",
            )
        )
    hedge_inverse_eligibility_report = HedgeInverseEligibilityReport(
        report_id=f"{learning_input.input_id}-HEDGE-INVERSE-ELIGIBILITY-REPORT",
        inverse_or_hedge_candidates_present=bool(inverse_or_hedge_candidates),
        full_policy_evidence_present=inverse_policy_complete or not inverse_or_hedge_candidates,
    )

    forward_outcome_label_report = ForwardOutcomeLabelReport(
        report_id=f"{learning_input.input_id}-FORWARD-OUTCOME-LABEL-REPORT",
        available_at_safe_label_boundary=learning_input.forward_outcome_label.available_at_safe_label_boundary,
        forward_label_present=True,
    )
    if not learning_input.forward_outcome_label.available_at_safe_label_boundary:
        gap_entries.append(
            _gap(
                learning_input,
                "FUTURE-OUTCOME-LEAKAGE",
                RegimeAllocationLearningGapCategory.FUTURE_OUTCOME_LEAKAGE,
                "BLOCKING",
                "forward outcome label boundary is not available_at safe",
            )
        )

    reward_scoring_report = AllocationRewardScoringReport(
        report_id=f"{learning_input.input_id}-ALLOCATION-REWARD-SCORING-REPORT",
        risk_adjusted_return=learning_input.reward_scoring_policy.risk_adjusted_return,
        max_drawdown_penalty=learning_input.reward_scoring_policy.max_drawdown_penalty,
        turnover_penalty=learning_input.reward_scoring_policy.turnover_penalty,
        volatility_penalty=learning_input.reward_scoring_policy.volatility_penalty,
        benchmark_relative_performance=learning_input.reward_scoring_policy.benchmark_relative_performance,
        tail_risk_penalty=learning_input.reward_scoring_policy.tail_risk_penalty,
        action_feasibility_penalty=learning_input.reward_scoring_policy.action_feasibility_penalty,
    )

    if learning_input.regime_event_leakage_detected:
        gap_entries.append(
            _gap(
                learning_input,
                "FUTURE-REGIME-EVENT-LEAKAGE",
                RegimeAllocationLearningGapCategory.FUTURE_REGIME_EVENT_LEAKAGE,
                "BLOCKING",
                "future regime or event leakage detected",
            )
        )
    if learning_input.future_outcome_leakage_detected:
        gap_entries.append(
            _gap(
                learning_input,
                "FUTURE-OUTCOME-LEAKAGE-FLAG",
                RegimeAllocationLearningGapCategory.FUTURE_OUTCOME_LEAKAGE,
                "BLOCKING",
                "future outcome leakage detected",
            )
        )
    if learning_input.dependency_status.current_survivors_only_dependency:
        gap_entries.append(
            _gap(
                learning_input,
                "CURRENT-SURVIVORS-ONLY-DEPENDENCY",
                RegimeAllocationLearningGapCategory.CURRENT_SURVIVORS_ONLY_DEPENDENCY,
                "BLOCKING",
                "current survivors only dependency blocks training-ready dataset",
            )
        )
    if learning_input.dependency_status.point_in_time_dataset_decision != "TRAINING_READY":
        gap_entries.append(
            _gap(
                learning_input,
                "MISSING-POINT-IN-TIME-GATE",
                RegimeAllocationLearningGapCategory.MISSING_POINT_IN_TIME_GATE,
                "WARNING",
                "point-in-time dataset is not training-ready",
            )
        )
    if learning_input.dependency_status.walk_forward_validation_decision is None:
        gap_entries.append(
            _gap(
                learning_input,
                "MISSING-WALK-FORWARD-EVIDENCE",
                RegimeAllocationLearningGapCategory.MISSING_WALK_FORWARD_EVIDENCE,
                "WARNING",
                "walk-forward validation evidence is missing",
            )
        )
    if not learning_input.dependency_status.ensemble_promotion_refs_present:
        gap_entries.append(
            _gap(
                learning_input,
                "MISSING-ENSEMBLE-REFS",
                RegimeAllocationLearningGapCategory.MISSING_ENSEMBLE_REFS,
                "WARNING",
                "ensemble promotion references are missing",
            )
        )

    leakage_report = RegimeAllocationLeakageReport(
        report_id=f"{learning_input.input_id}-REGIME-ALLOCATION-LEAKAGE-REPORT",
        regime_event_leakage_detected=learning_input.regime_event_leakage_detected,
        future_outcome_leakage_detected=learning_input.future_outcome_leakage_detected
        or not learning_input.forward_outcome_label.available_at_safe_label_boundary,
        current_survivors_only_dependency=learning_input.dependency_status.current_survivors_only_dependency,
    )

    safety_report = RegimeAllocationLearningSafetyReport(
        safety_report_id=f"{learning_input.input_id}-SAFETY-REPORT",
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

    decision, reason = _decide(learning_input, gap_entries)
    readiness_report = LearningDatasetReadinessReport(
        report_id=f"{learning_input.input_id}-LEARNING-DATASET-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    gap_entries.append(
        _gap(
            learning_input,
            "DATASET-REPORT-GENERATED",
            RegimeAllocationLearningGapCategory.DATASET_REPORT_GENERATED,
            "REPORT_ONLY",
            "regime allocation learning dataset report generated",
        )
    )
    gap_report = RegimeAllocationLearningGapReport(
        gap_report_id=f"{learning_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for gap in gap_entries if gap.severity == "BLOCKING"),
        warning_gap_count=sum(1 for gap in gap_entries if gap.severity == "WARNING"),
    )
    return learning_input.model_copy(
        update={
            "regime_feature_report": regime_feature_report,
            "action_candidate_report": action_candidate_report,
            "hedge_inverse_eligibility_report": hedge_inverse_eligibility_report,
            "forward_outcome_label_report": forward_outcome_label_report,
            "allocation_reward_scoring_report": reward_scoring_report,
            "regime_allocation_leakage_report": leakage_report,
            "learning_dataset_readiness_report": readiness_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _decide(learning_input: RegimeAllocationLearningInput, gap_entries: list[RegimeAllocationLearningGapEntry]):
    blocking = [entry for entry in gap_entries if entry.severity == "BLOCKING"]
    warnings = [entry for entry in gap_entries if entry.severity == "WARNING"]
    if blocking:
        return LearningDatasetReadinessDecision.BLOCKED, blocking[0].message
    if learning_input.dependency_status.point_in_time_dataset_decision is None:
        return LearningDatasetReadinessDecision.GAP, "point-in-time gate evidence is missing"
    if warnings:
        return LearningDatasetReadinessDecision.GAP, warnings[0].message
    if learning_input.dependency_status.point_in_time_dataset_decision == "TRAINING_READY":
        return LearningDatasetReadinessDecision.TRAINING_READY, "regime/action/outcome dataset is training-ready"
    return LearningDatasetReadinessDecision.RESEARCH_READY, "exploratory regime allocation analysis only"


def _gap(learning_input, suffix, category, severity, message):
    return RegimeAllocationLearningGapEntry(
        gap_id=f"{learning_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
