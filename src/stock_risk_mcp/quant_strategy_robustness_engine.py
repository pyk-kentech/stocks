from __future__ import annotations

from stock_risk_mcp.quant_strategy_robustness_guard import (
    validate_quant_strategy_robustness_metadata_safety,
)
from stock_risk_mcp.quant_strategy_robustness_models import (
    QuantStrategyDataSnoopingReport,
    QuantStrategyDiversificationReport,
    QuantStrategyPointInTimeLeakageReport,
    QuantStrategyRegimeReadinessReport,
    QuantStrategyRobustnessDecision,
    QuantStrategyRobustnessGapCategory,
    QuantStrategyRobustnessGapEntry,
    QuantStrategyRobustnessGapReport,
    QuantStrategyRobustnessInput,
    QuantStrategyRobustnessReport,
    QuantStrategyRobustnessSafetyReport,
    QuantStrategySurvivorshipBiasReport,
    QuantStrategyWalkForwardPolicyReport,
)


_ALPHA_FAMILY_MINIMUM = 3
_MAX_CORRELATION = 0.80
_MAX_DRAWDOWN_COMOVEMENT = 0.70


def build_quant_strategy_robustness(
    robustness_input: QuantStrategyRobustnessInput,
) -> QuantStrategyRobustnessInput:
    gap_entries: list[QuantStrategyRobustnessGapEntry] = []
    for audit in robustness_input.audit_records:
        validate_quant_strategy_robustness_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="quant strategy robustness",
        )

    survivorship_report = _build_survivorship_bias_report(robustness_input, gap_entries)
    point_in_time_report = _build_point_in_time_report(robustness_input, gap_entries)
    walk_forward_report = _build_walk_forward_report(robustness_input, gap_entries)
    data_snooping_report = _build_data_snooping_report(robustness_input, gap_entries)
    diversification_report = _build_diversification_report(robustness_input, gap_entries)
    regime_report = _build_regime_report(robustness_input, gap_entries)
    safety_report = _build_safety_report(robustness_input)
    decision, reason = _decide(
        survivorship_report=survivorship_report,
        point_in_time_report=point_in_time_report,
        walk_forward_report=walk_forward_report,
        data_snooping_report=data_snooping_report,
        diversification_report=diversification_report,
        regime_report=regime_report,
        gap_entries=gap_entries,
    )
    readiness_report = QuantStrategyRobustnessReport(
        readiness_report_id=f"{robustness_input.input_id}-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
        current_survivors_only=robustness_input.universe_policy.universe_mode.value == "CURRENT_SURVIVORS_ONLY",
        point_in_time_ready=point_in_time_report.available_at_complete and not point_in_time_report.future_leakage_detected,
        walk_forward_ready=walk_forward_report.walk_forward_ready,
        data_snooping_risk_flagged=data_snooping_report.excessive_parameter_search_flagged,
        diversification_ready=diversification_report.diversification_ready,
        regime_ready=regime_report.regime_ready,
    )
    gap_entries.append(
        QuantStrategyRobustnessGapEntry(
            gap_id=f"{robustness_input.input_id}-ROBUSTNESS-REPORT-GENERATED",
            gap_category=QuantStrategyRobustnessGapCategory.ROBUSTNESS_REPORT_GENERATED,
            severity="REPORT_ONLY",
            message="quant strategy robustness report generated",
        )
    )
    gap_report = QuantStrategyRobustnessGapReport(
        gap_report_id=f"{robustness_input.input_id}-ROBUSTNESS-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for gap in gap_entries if gap.severity == "BLOCKING"),
        warning_gap_count=sum(1 for gap in gap_entries if gap.severity == "WARNING"),
    )
    return robustness_input.model_copy(
        update={
            "robustness_readiness_report": readiness_report,
            "survivorship_bias_report": survivorship_report,
            "point_in_time_leakage_report": point_in_time_report,
            "walk_forward_policy_report": walk_forward_report,
            "data_snooping_report": data_snooping_report,
            "strategy_diversification_report": diversification_report,
            "regime_readiness_report": regime_report,
            "robustness_gap_report": gap_report,
            "robustness_safety_report": safety_report,
        }
    )


def _build_survivorship_bias_report(robustness_input, gap_entries):
    policy = robustness_input.universe_policy
    findings: list[str] = []
    training_grade_allowed = policy.universe_mode.value == "POINT_IN_TIME_HISTORICAL"
    if policy.universe_mode.value == "CURRENT_SURVIVORS_ONLY":
        findings.append("current survivors only universe")
        gap_entries.append(_gap(robustness_input, "SURVIVORSHIP-CURRENT-ONLY", QuantStrategyRobustnessGapCategory.SURVIVORSHIP_CURRENT_ONLY_TRAINING_CLAIM_BLOCKED, "WARNING", "current survivors only dataset is not training-grade"))
        training_grade_allowed = False
    if not policy.historical_universe_snapshots_available:
        gap_entries.append(_gap(robustness_input, "SURVIVORSHIP-HISTORICAL-UNIVERSE-MISSING", QuantStrategyRobustnessGapCategory.SURVIVORSHIP_HISTORICAL_UNIVERSE_MISSING, "WARNING", "historical universe snapshots missing"))
        training_grade_allowed = False
    if not policy.delisted_handled:
        gap_entries.append(_gap(robustness_input, "DELISTING-POLICY-MISSING", QuantStrategyRobustnessGapCategory.DELISTING_POLICY_MISSING, "WARNING", "delisting handling missing"))
        training_grade_allowed = False
    return QuantStrategySurvivorshipBiasReport(
        report_id=f"{robustness_input.input_id}-SURVIVORSHIP-REPORT",
        universe_mode=policy.universe_mode,
        training_grade_allowed=training_grade_allowed,
        findings=findings,
    )


def _build_point_in_time_report(robustness_input, gap_entries):
    policy = robustness_input.point_in_time_policy
    available_at_complete = all(
        (
            policy.price_features_have_available_at,
            policy.fundamental_features_have_available_at,
            policy.index_features_have_available_at,
            policy.macro_features_have_available_at,
            policy.event_features_have_available_at,
        )
    )
    corporate_action_complete = all(
        (
            policy.corporate_action_policy_present,
            policy.split_policy_present,
            policy.dividend_policy_present,
            policy.symbol_change_policy_present,
            policy.delisting_policy_present,
        )
    )
    findings: list[str] = []
    if not available_at_complete:
        gap_entries.append(_gap(robustness_input, "AVAILABLE-AT-MISSING", QuantStrategyRobustnessGapCategory.POINT_IN_TIME_AVAILABLE_AT_MISSING, "WARNING", "available_at timestamps are incomplete"))
        findings.append("available_at incomplete")
    if not policy.future_data_leakage_blocked:
        gap_entries.append(_gap(robustness_input, "FUTURE-LEAKAGE-DETECTED", QuantStrategyRobustnessGapCategory.FUTURE_DATA_LEAKAGE_DETECTED, "BLOCKING", "future data leakage detected"))
        findings.append("future leakage detected")
    if not corporate_action_complete:
        gap_entries.append(_gap(robustness_input, "CORPORATE-ACTION-POLICY-MISSING", QuantStrategyRobustnessGapCategory.CORPORATE_ACTION_POLICY_MISSING, "WARNING", "corporate action handling policy is incomplete"))
        findings.append("corporate action policy incomplete")
    return QuantStrategyPointInTimeLeakageReport(
        report_id=f"{robustness_input.input_id}-POINT-IN-TIME-REPORT",
        available_at_complete=available_at_complete,
        future_leakage_detected=not policy.future_data_leakage_blocked,
        corporate_action_policy_complete=corporate_action_complete,
        findings=findings,
    )


def _build_walk_forward_report(robustness_input, gap_entries):
    policy = robustness_input.walk_forward_policy
    findings: list[str] = []
    repeated_final_test_tuning_flagged = policy.final_test_period_reused_for_tuning or policy.repeated_final_test_tuning_count > 0
    excessive_parameter_search_flagged = policy.parameter_search_count > policy.max_parameter_search_count
    walk_forward_ready = True
    if repeated_final_test_tuning_flagged:
        gap_entries.append(_gap(robustness_input, "FINAL-TEST-RETUNING", QuantStrategyRobustnessGapCategory.FINAL_TEST_RETUNING_DETECTED, "BLOCKING", "final test period retuning detected"))
        findings.append("final test retuning detected")
        walk_forward_ready = False
    if excessive_parameter_search_flagged:
        gap_entries.append(_gap(robustness_input, "EXCESSIVE-PARAMETER-SEARCH", QuantStrategyRobustnessGapCategory.EXCESSIVE_PARAMETER_SEARCH, "WARNING", "parameter search count is excessive"))
        findings.append("excessive parameter search")
        walk_forward_ready = False
    if not policy.period_stability_metrics_present:
        gap_entries.append(_gap(robustness_input, "PERIOD-STABILITY-MISSING", QuantStrategyRobustnessGapCategory.PERIOD_STABILITY_MISSING, "WARNING", "period stability metrics are missing"))
        findings.append("period stability missing")
        walk_forward_ready = False
    return QuantStrategyWalkForwardPolicyReport(
        report_id=f"{robustness_input.input_id}-WALK-FORWARD-REPORT",
        walk_forward_ready=walk_forward_ready,
        repeated_final_test_tuning_flagged=repeated_final_test_tuning_flagged,
        excessive_parameter_search_flagged=excessive_parameter_search_flagged,
        findings=findings,
    )


def _build_data_snooping_report(robustness_input, gap_entries):
    policy = robustness_input.walk_forward_policy
    lineage_present = robustness_input.experiment_registry_ref is not None
    if not lineage_present:
        gap_entries.append(_gap(robustness_input, "EXPERIMENT-LINEAGE-MISSING", QuantStrategyRobustnessGapCategory.EXPERIMENT_LINEAGE_MISSING, "WARNING", "experiment lineage reference is missing"))
    return QuantStrategyDataSnoopingReport(
        report_id=f"{robustness_input.input_id}-DATA-SNOOPING-REPORT",
        parameter_search_count=policy.parameter_search_count,
        excessive_parameter_search_flagged=policy.parameter_search_count > policy.max_parameter_search_count,
        period_stability_metrics_present=policy.period_stability_metrics_present,
        experiment_lineage_present=lineage_present,
        findings=[] if lineage_present else ["experiment lineage missing"],
    )


def _build_diversification_report(robustness_input, gap_entries):
    policy = robustness_input.diversification_policy
    family_count = len(policy.alpha_candidate_families)
    correlation_flagged = policy.max_pairwise_strategy_correlation > _MAX_CORRELATION
    drawdown_flagged = policy.max_drawdown_comovement > _MAX_DRAWDOWN_COMOVEMENT
    diversification_ready = family_count >= _ALPHA_FAMILY_MINIMUM and not correlation_flagged and not drawdown_flagged
    findings: list[str] = []
    if family_count < _ALPHA_FAMILY_MINIMUM:
        gap_entries.append(_gap(robustness_input, "DIVERSIFICATION-TOO-NARROW", QuantStrategyRobustnessGapCategory.STRATEGY_DIVERSIFICATION_TOO_NARROW, "WARNING", "strategy family coverage is too narrow"))
        findings.append("strategy family coverage too narrow")
    if correlation_flagged:
        gap_entries.append(_gap(robustness_input, "STRATEGY-CORRELATION-TOO-HIGH", QuantStrategyRobustnessGapCategory.STRATEGY_CORRELATION_TOO_HIGH, "WARNING", "strategy correlation is too high"))
        findings.append("strategy correlation too high")
    if drawdown_flagged:
        gap_entries.append(_gap(robustness_input, "DRAWDOWN-COMOVEMENT-TOO-HIGH", QuantStrategyRobustnessGapCategory.DRAWDOWN_COMOVEMENT_TOO_HIGH, "WARNING", "drawdown co-movement is too high"))
        findings.append("drawdown co-movement too high")
    return QuantStrategyDiversificationReport(
        report_id=f"{robustness_input.input_id}-DIVERSIFICATION-REPORT",
        family_count=family_count,
        diversification_ready=diversification_ready,
        strategy_correlation_flagged=correlation_flagged,
        drawdown_comovement_flagged=drawdown_flagged,
        findings=findings,
    )


def _build_regime_report(robustness_input, gap_entries):
    policy = robustness_input.regime_policy
    missing_bucket_count = max(policy.required_bucket_count - policy.evaluated_bucket_count, 0)
    regime_ready = missing_bucket_count == 0
    findings: list[str] = []
    if not regime_ready:
        gap_entries.append(_gap(robustness_input, "REGIME-BUCKET-EVIDENCE-MISSING", QuantStrategyRobustnessGapCategory.REGIME_BUCKET_EVIDENCE_MISSING, "WARNING", "regime bucket evaluation is incomplete"))
        findings.append("regime bucket evaluation incomplete")
    return QuantStrategyRegimeReadinessReport(
        report_id=f"{robustness_input.input_id}-REGIME-REPORT",
        regime_ready=regime_ready,
        evaluated_bucket_count=policy.evaluated_bucket_count,
        missing_bucket_count=missing_bucket_count,
        findings=findings,
    )


def _build_safety_report(robustness_input):
    return QuantStrategyRobustnessSafetyReport(
        safety_report_id=f"{robustness_input.input_id}-SAFETY-REPORT",
        blocked_capabilities=[
            "LIVE_TRADING_BLOCKED",
            "REAL_ORDER_BLOCKED",
            "ACCOUNT_MUTATION_BLOCKED",
            "BROKER_API_BLOCKED",
            "NETWORK_BLOCKED",
            "AUTONOMOUS_TRADING_BLOCKED",
        ],
        findings=[
            "local_offline_report_only=true",
            "training_readiness_is_non_executable=true",
        ],
    )


def _decide(*, survivorship_report, point_in_time_report, walk_forward_report, data_snooping_report, diversification_report, regime_report, gap_entries):
    if point_in_time_report.future_leakage_detected:
        return QuantStrategyRobustnessDecision.BLOCKED, "future data leakage detected"
    blocking = [gap for gap in gap_entries if gap.severity == "BLOCKING"]
    warnings = [gap for gap in gap_entries if gap.severity == "WARNING"]
    if blocking:
        return QuantStrategyRobustnessDecision.BLOCKED, blocking[0].message
    training_ready = all(
        (
            survivorship_report.training_grade_allowed,
            point_in_time_report.available_at_complete,
            point_in_time_report.corporate_action_policy_complete,
            walk_forward_report.walk_forward_ready,
            not data_snooping_report.excessive_parameter_search_flagged,
            data_snooping_report.experiment_lineage_present,
            diversification_report.diversification_ready,
            regime_report.regime_ready,
        )
    )
    if training_ready:
        return QuantStrategyRobustnessDecision.TRAINING_READY, "training-grade robustness evidence is complete"
    if warnings:
        if survivorship_report.universe_mode.value == "CURRENT_SURVIVORS_ONLY":
            return QuantStrategyRobustnessDecision.RESEARCH_READY, "current survivor universe is research-only"
        return QuantStrategyRobustnessDecision.GAP, warnings[0].message
    return QuantStrategyRobustnessDecision.RESEARCH_READY, "local offline robustness checks are available for research only"


def _gap(robustness_input, suffix, category, severity, message):
    return QuantStrategyRobustnessGapEntry(
        gap_id=f"{robustness_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
