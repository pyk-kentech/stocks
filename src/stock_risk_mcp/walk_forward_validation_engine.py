from __future__ import annotations

from stock_risk_mcp.walk_forward_validation_guard import (
    validate_walk_forward_validation_metadata_safety,
)
from stock_risk_mcp.walk_forward_validation_models import (
    DataSnoopingReport,
    ExperimentLineageReport,
    FinalTestContaminationReport,
    ParameterSearchPressureReport,
    PromotionReadinessReport,
    StabilityReport,
    WalkForwardSplitReport,
    WalkForwardValidationDecision,
    WalkForwardValidationGapCategory,
    WalkForwardValidationGapEntry,
    WalkForwardValidationGapReport,
    WalkForwardValidationInput,
    WalkForwardValidationSafetyReport,
)


def build_walk_forward_validation(
    validation_input: WalkForwardValidationInput,
) -> WalkForwardValidationInput:
    gap_entries: list[WalkForwardValidationGapEntry] = []
    for audit in validation_input.audit_records:
        validate_walk_forward_validation_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="walk forward validation",
        )

    clean_non_overlapping_split = _is_clean_non_overlapping_split(validation_input)
    forward_paper_present = validation_input.split.forward_paper_window is not None
    if not clean_non_overlapping_split:
        gap_entries.append(_gap(validation_input, "OVERLAPPING-WINDOWS", WalkForwardValidationGapCategory.OVERLAPPING_WINDOWS_DETECTED, "BLOCKING", "overlapping train/validation/test/forward windows detected"))
    if validation_input.config.paper_ready_requires_forward_window and not forward_paper_present:
        gap_entries.append(_gap(validation_input, "FORWARD-PAPER-WINDOW-MISSING", WalkForwardValidationGapCategory.FORWARD_PAPER_WINDOW_MISSING, "WARNING", "forward-paper window is missing"))

    split_report = WalkForwardSplitReport(
        report_id=f"{validation_input.input_id}-WALK-FORWARD-SPLIT-REPORT",
        clean_non_overlapping_split=clean_non_overlapping_split,
        mode=validation_input.split.mode,
        forward_paper_window_present=forward_paper_present,
    )

    lineage_present = validation_input.experiment_lineage is not None
    if not lineage_present:
        gap_entries.append(_gap(validation_input, "EXPERIMENT-LINEAGE-MISSING", WalkForwardValidationGapCategory.EXPERIMENT_LINEAGE_MISSING, "WARNING", "experiment lineage is missing"))
    lineage_report = ExperimentLineageReport(
        report_id=f"{validation_input.input_id}-EXPERIMENT-LINEAGE-REPORT",
        lineage_present=lineage_present,
        final_test_access_count=validation_input.experiment_lineage.final_test_access_count if lineage_present else 0,
        validation_reuse_count=validation_input.experiment_lineage.validation_reuse_count if lineage_present else 0,
    )

    repeated_final_test_tuning = False
    final_test_contamination = False
    unregistered_parameter_mutation = False
    if validation_input.experiment_lineage is not None:
        repeated_final_test_tuning = validation_input.experiment_lineage.final_test_access_count > 1
        final_test_contamination = repeated_final_test_tuning
        unregistered_parameter_mutation = validation_input.experiment_lineage.unregistered_parameter_mutation_detected
    if repeated_final_test_tuning:
        gap_entries.append(_gap(validation_input, "FINAL-TEST-REPEATED-TUNING", WalkForwardValidationGapCategory.FINAL_TEST_REPEATED_TUNING, "BLOCKING", "repeated tuning on final test period detected"))
    if final_test_contamination:
        gap_entries.append(_gap(validation_input, "FINAL-TEST-CONTAMINATION", WalkForwardValidationGapCategory.FINAL_TEST_CONTAMINATION_DETECTED, "BLOCKING", "final test contamination detected"))
    if unregistered_parameter_mutation:
        gap_entries.append(_gap(validation_input, "UNREGISTERED-PARAMETER-MUTATION", WalkForwardValidationGapCategory.UNREGISTERED_PARAMETER_MUTATION, "WARNING", "unregistered parameter mutation detected"))

    excessive_parameter_search = validation_input.parameter_search_count > validation_input.config.max_parameter_search_count
    hidden_failed_trial_pressure = validation_input.hidden_failed_trial_count > validation_input.config.max_hidden_failed_trials
    if excessive_parameter_search:
        gap_entries.append(_gap(validation_input, "EXCESSIVE-PARAMETER-SEARCH", WalkForwardValidationGapCategory.EXCESSIVE_PARAMETER_SEARCH, "WARNING", "excessive parameter search count"))
    if hidden_failed_trial_pressure:
        gap_entries.append(_gap(validation_input, "HIDDEN-FAILED-TRIAL-PRESSURE", WalkForwardValidationGapCategory.HIDDEN_FAILED_TRIAL_PRESSURE, "WARNING", "hidden failed trial pressure is too high"))
    if validation_input.test_period_cherry_picking_detected:
        gap_entries.append(_gap(validation_input, "TEST-PERIOD-CHERRY-PICKING", WalkForwardValidationGapCategory.TEST_PERIOD_CHERRY_PICKING, "BLOCKING", "test-period cherry-picking detected"))

    data_snooping_report = DataSnoopingReport(
        report_id=f"{validation_input.input_id}-DATA-SNOOPING-REPORT",
        excessive_parameter_search_flagged=excessive_parameter_search,
        hidden_failed_trial_pressure_flagged=hidden_failed_trial_pressure,
        test_period_cherry_picking_flagged=validation_input.test_period_cherry_picking_detected,
        unregistered_parameter_mutation_flagged=unregistered_parameter_mutation,
    )
    parameter_search_report = ParameterSearchPressureReport(
        report_id=f"{validation_input.input_id}-PARAMETER-SEARCH-PRESSURE-REPORT",
        parameter_search_count=validation_input.parameter_search_count,
        hidden_failed_trial_count=validation_input.hidden_failed_trial_count,
        excessive_parameter_search_flagged=excessive_parameter_search,
        hidden_failed_trial_pressure_flagged=hidden_failed_trial_pressure,
    )
    final_test_report = FinalTestContaminationReport(
        report_id=f"{validation_input.input_id}-FINAL-TEST-CONTAMINATION-REPORT",
        repeated_final_test_tuning_flagged=repeated_final_test_tuning,
        final_test_contamination_detected=final_test_contamination,
    )

    stable_multi_fold = validation_input.stability_evidence.fold_count >= 3 and validation_input.stability_evidence.stable_fold_count >= 2
    if validation_input.stability_evidence.single_period_only_success:
        gap_entries.append(_gap(validation_input, "SINGLE-PERIOD-ONLY-SUCCESS", WalkForwardValidationGapCategory.SINGLE_PERIOD_ONLY_SUCCESS, "WARNING", "strategy only works in one historical slice"))
    if not stable_multi_fold:
        gap_entries.append(_gap(validation_input, "MULTI-FOLD-STABILITY-MISSING", WalkForwardValidationGapCategory.MULTI_FOLD_STABILITY_MISSING, "WARNING", "multiple stable folds are missing"))
    if not validation_input.regime_bucket_reference_present:
        gap_entries.append(_gap(validation_input, "REGIME-BUCKET-REFERENCE-MISSING", WalkForwardValidationGapCategory.REGIME_BUCKET_REFERENCE_MISSING, "WARNING", "regime bucket reference missing"))
    stability_report = StabilityReport(
        report_id=f"{validation_input.input_id}-STABILITY-REPORT",
        multiple_stable_folds_present=stable_multi_fold,
        single_period_only_success_flagged=validation_input.stability_evidence.single_period_only_success,
        drawdown_stable=validation_input.stability_evidence.drawdown_stable,
        hit_rate_stable=validation_input.stability_evidence.hit_rate_stable,
        return_stable=validation_input.stability_evidence.return_stable,
        risk_adjusted_metric_stable=validation_input.stability_evidence.risk_adjusted_metric_stable,
    )

    safety_report = WalkForwardValidationSafetyReport(
        safety_report_id=f"{validation_input.input_id}-SAFETY-REPORT",
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
    decision, reason = _decide(
        validation_input=validation_input,
        clean_non_overlapping_split=clean_non_overlapping_split,
        forward_paper_present=forward_paper_present,
        lineage_present=lineage_present,
        excessive_parameter_search=excessive_parameter_search,
        hidden_failed_trial_pressure=hidden_failed_trial_pressure,
        repeated_final_test_tuning=repeated_final_test_tuning,
        final_test_contamination=final_test_contamination,
        stable_multi_fold=stable_multi_fold,
        gap_entries=gap_entries,
    )
    promotion_report = PromotionReadinessReport(
        report_id=f"{validation_input.input_id}-PROMOTION-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    gap_entries.append(_gap(validation_input, "WALK-FORWARD-REPORT-GENERATED", WalkForwardValidationGapCategory.WALK_FORWARD_REPORT_GENERATED, "REPORT_ONLY", "walk-forward validation report generated"))
    gap_report = WalkForwardValidationGapReport(
        gap_report_id=f"{validation_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for gap in gap_entries if gap.severity == "BLOCKING"),
        warning_gap_count=sum(1 for gap in gap_entries if gap.severity == "WARNING"),
    )
    return validation_input.model_copy(
        update={
            "walk_forward_split_report": split_report,
            "data_snooping_report": data_snooping_report,
            "experiment_lineage_report": lineage_report,
            "parameter_search_pressure_report": parameter_search_report,
            "final_test_contamination_report": final_test_report,
            "stability_report": stability_report,
            "promotion_readiness_report": promotion_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _is_clean_non_overlapping_split(validation_input: WalkForwardValidationInput) -> bool:
    windows = [
        validation_input.split.train_window,
        validation_input.split.validation_window,
        validation_input.split.test_window,
    ]
    if validation_input.split.forward_paper_window is not None:
        windows.append(validation_input.split.forward_paper_window)
    ordered = sorted(windows, key=lambda window: window.start_at)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.end_at > current.start_at:
            return False
    return True


def _decide(
    *,
    validation_input: WalkForwardValidationInput,
    clean_non_overlapping_split: bool,
    forward_paper_present: bool,
    lineage_present: bool,
    excessive_parameter_search: bool,
    hidden_failed_trial_pressure: bool,
    repeated_final_test_tuning: bool,
    final_test_contamination: bool,
    stable_multi_fold: bool,
    gap_entries: list[WalkForwardValidationGapEntry],
):
    blocking = [gap for gap in gap_entries if gap.severity == "BLOCKING"]
    warnings = [gap for gap in gap_entries if gap.severity == "WARNING"]
    if blocking:
        return WalkForwardValidationDecision.BLOCKED, blocking[0].message
    if not clean_non_overlapping_split:
        return WalkForwardValidationDecision.REJECTED, "invalid overlapping split"
    if not lineage_present:
        return WalkForwardValidationDecision.GAP, "experiment lineage is missing"
    if not stable_multi_fold:
        return WalkForwardValidationDecision.GAP, "multiple stable folds are missing"
    if excessive_parameter_search or hidden_failed_trial_pressure:
        return WalkForwardValidationDecision.GAP, "search pressure remains too high"
    if validation_input.stability_evidence.single_period_only_success:
        return WalkForwardValidationDecision.GAP, "single-period-only success is insufficient"
    if validation_input.config.paper_ready_requires_forward_window and not forward_paper_present:
        return WalkForwardValidationDecision.GAP, "forward-paper window is missing"
    if warnings:
        return WalkForwardValidationDecision.VALIDATION_READY, warnings[0].message
    if forward_paper_present:
        return WalkForwardValidationDecision.PAPER_READY, "stable walk-forward validation and forward-paper evidence are present"
    return WalkForwardValidationDecision.VALIDATION_READY, "clean walk-forward validation is present"


def _gap(validation_input, suffix, category, severity, message):
    return WalkForwardValidationGapEntry(
        gap_id=f"{validation_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
