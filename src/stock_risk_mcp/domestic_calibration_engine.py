from __future__ import annotations

from stock_risk_mcp.domestic_calibration_models import (
    CalibrationPack,
    CalibrationPackCoverageReport,
    CalibrationPackMetrics,
    CalibrationRunResult,
    CalibrationSafetyBoundary,
    CalibrationValidationReport,
    CandidatePolicySummary,
    DOMESTIC_CALIBRATION_METADATA,
    DomesticCalibrationFixture,
    PolicyComparisonReport,
    PolicyRegressionReport,
    PromotionGateReport,
    PromotionGateStatus,
    SingleReplayComparisonResult,
)
from stock_risk_mcp.strategy_track_models import StrategyTrack


def build_domestic_calibration_validation_report(
    fixture: DomesticCalibrationFixture,
) -> CalibrationValidationReport:
    return CalibrationValidationReport(
        calibration_run_id=fixture.calibration_run_config.calibration_run_id,
        strategy_track=fixture.calibration_run_config.strategy_track,
        market_id=str(fixture.calibration_input_set.market_profile_summary["market_id"]).upper(),
        replay_report_count=len(fixture.calibration_input_set.replay_reports),
    )


def _candidate_summary(report, candidate) -> CandidatePolicySummary:
    metrics = report.metrics
    strictness_penalty = int(max(candidate.scanner_threshold_config.volume_spike_threshold - 2.0, 0) * 10)
    looseness_bonus = int(max(2.0 - candidate.scanner_threshold_config.volume_spike_threshold, 0) * 10)
    coverage_score = max(
        0,
        min(
            100,
            50
            + metrics.total_events_processed * 10
            + looseness_bonus
            - strictness_penalty
            - candidate.evaluation_threshold_config.minimum_technical_score // 10,
        ),
    )
    safety_score = max(
        0,
        100
        - metrics.unsafe_trigger_rejection_count * 100
        - metrics.domestic_only_rejection_count * 100
        - metrics.quality_failure_count * 10,
    )
    stability_score = max(
        0,
        min(
            100,
            40
            + len(report.windows) * 20
            - abs(candidate.scanner_threshold_config.watchlist_add_threshold - 70)
            // 2,
        ),
    )
    return CandidatePolicySummary(
        candidate_policy_id=candidate.policy_id,
        coverage_score=coverage_score,
        safety_score=safety_score,
        stability_score=stability_score,
        candidates_generated=metrics.generated_scanner_candidates,
        candidates_blocked=metrics.blocked_candidate_count,
        report_only_count=metrics.report_only_candidate_count,
        non_actionable_count=metrics.non_actionable_candidate_count,
        stale_data_block_count=metrics.stale_events,
        quality_block_count=metrics.quality_failure_count,
        profitability_block_count=metrics.profitability_blocked_count,
        technical_evidence_block_count=metrics.technical_evidence_blocked_count,
        unsafe_trigger_rejection_count=metrics.unsafe_trigger_rejection_count,
        false_positive_proxy_placeholder=max(0, metrics.watchlist_add_count - 1),
        missed_opportunity_proxy_placeholder=max(0, 3 - metrics.watchlist_add_count),
    )


def _single_run_result(fixture: DomesticCalibrationFixture, index: int, report) -> SingleReplayComparisonResult:
    candidate_summaries = [_candidate_summary(report, candidate) for candidate in fixture.candidate_policies]
    regression_findings: list[str] = []
    if report.metrics.unsafe_trigger_rejection_count:
        regression_findings.append("UNSAFE_TRIGGER_REJECTION_REGRESSION")
    if report.metrics.domestic_only_rejection_count:
        regression_findings.append("DOMESTIC_ONLY_REGRESSION")
    if report.metrics.report_only_candidate_count:
        regression_findings.append("REPORT_ONLY_POLICY_REGRESSION")
    return SingleReplayComparisonResult(
        comparison_result_id=f"{fixture.run_id}-single-run-{index}",
        replay_report_id=report.report_id,
        baseline_policy_id=fixture.baseline_policy.policy_id,
        candidate_summaries=candidate_summaries,
        event_trace_reference=f"{report.report_id}#step_results",
        window_summary_reference=f"{report.report_id}#windows",
        regression_findings=regression_findings,
        warnings=list(report.warnings),
        block_reasons=list(report.block_reasons),
        promotion_eligible=False,
    )


def _coverage_report(fixture: DomesticCalibrationFixture) -> CalibrationPackCoverageReport:
    required = set(fixture.calibration_run_config.required_scenario_families)
    observed = set(fixture.calibration_input_set.scenario_family_labels)
    observed_window_count = sum(len(report.windows) for report in fixture.calibration_input_set.replay_reports)
    missing = sorted(required - observed)
    diversity_warnings = []
    if len(fixture.calibration_input_set.replay_reports) == 1:
        diversity_warnings.append("SINGLE_RUN_ONLY_EVIDENCE")
    if missing:
        diversity_warnings.append("MISSING_REQUIRED_SCENARIO_FAMILY")
    return CalibrationPackCoverageReport(
        required_scenario_families=sorted(required),
        observed_scenario_families=sorted(observed),
        missing_scenario_families=missing,
        required_replay_count=fixture.calibration_run_config.minimum_replay_count,
        observed_replay_count=len(fixture.calibration_input_set.replay_reports),
        required_window_count=fixture.calibration_run_config.minimum_window_count,
        observed_window_count=observed_window_count,
        diversity_warnings=diversity_warnings,
        coverage_pass=(
            len(fixture.calibration_input_set.replay_reports) >= fixture.calibration_run_config.minimum_replay_count
            and observed_window_count >= fixture.calibration_run_config.minimum_window_count
            and not missing
        ),
    )


def _aggregate_pack_metrics(fixture: DomesticCalibrationFixture) -> CalibrationPackMetrics:
    reports = fixture.calibration_input_set.replay_reports
    windows = sum(len(report.windows) for report in reports)
    scenario_count = len(set(fixture.calibration_input_set.scenario_family_labels))
    safety_regression_count = sum(1 for report in reports if report.metrics.unsafe_trigger_rejection_count)
    stale_regression_count = sum(1 for report in reports if report.metrics.stale_events or report.metrics.report_only_candidate_count)
    domestic_regression_count = sum(1 for report in reports if report.metrics.domestic_only_rejection_count)
    observed_replay_count = len(reports)
    coverage_score = min(100, int((observed_replay_count / fixture.calibration_run_config.minimum_replay_count) * 50) + int((windows / fixture.calibration_run_config.minimum_window_count) * 50))
    safety_score = max(0, 100 - safety_regression_count * 100 - domestic_regression_count * 100)
    stability_score = min(100, 40 + windows * 20)
    return CalibrationPackMetrics(
        runs_evaluated=observed_replay_count,
        windows_evaluated=windows,
        scenario_family_count=scenario_count,
        replay_fixture_count=observed_replay_count,
        candidates_generated=sum(report.metrics.generated_scanner_candidates for report in reports),
        candidates_blocked=sum(report.metrics.blocked_candidate_count for report in reports),
        report_only_count=sum(report.metrics.report_only_candidate_count for report in reports),
        non_actionable_count=sum(report.metrics.non_actionable_candidate_count for report in reports),
        watchlist_add_remove_count=sum(report.metrics.watchlist_add_count + report.metrics.watchlist_remove_count for report in reports),
        stale_data_block_count=sum(report.metrics.stale_events for report in reports),
        quality_block_count=sum(report.metrics.quality_failure_count for report in reports),
        profitability_block_count=sum(report.metrics.profitability_blocked_count for report in reports),
        technical_evidence_block_count=sum(report.metrics.technical_evidence_blocked_count for report in reports),
        unsafe_trigger_rejection_count=sum(report.metrics.unsafe_trigger_rejection_count for report in reports),
        safety_regression_count=safety_regression_count,
        stale_data_regression_count=stale_regression_count,
        domestic_only_regression_count=domestic_regression_count,
        coverage_score=max(0, min(100, coverage_score)),
        safety_score=max(0, min(100, safety_score)),
        stability_score=max(0, min(100, stability_score)),
        false_positive_proxy_placeholder=max(0, sum(report.metrics.watchlist_add_count for report in reports) - observed_replay_count),
        missed_opportunity_proxy_placeholder=max(0, observed_replay_count * 2 - sum(report.metrics.watchlist_add_count for report in reports)),
    )


def _regression_report(fixture: DomesticCalibrationFixture) -> PolicyRegressionReport:
    reports = fixture.calibration_input_set.replay_reports
    return PolicyRegressionReport(
        report_id=f"{fixture.run_id}-regressions",
        safety_boundary_regressions=["UNSAFE_TRIGGER_REJECTION_REGRESSION"] if any(report.metrics.unsafe_trigger_rejection_count for report in reports) else [],
        domestic_only_regressions=["DOMESTIC_ONLY_REGRESSION"] if any(report.metrics.domestic_only_rejection_count for report in reports) else [],
        stale_data_policy_regressions=["STALE_DATA_POLICY_REGRESSION"] if any(report.metrics.stale_events for report in reports) else [],
        report_only_policy_regressions=["REPORT_ONLY_POLICY_REGRESSION"] if any(report.metrics.report_only_candidate_count for report in reports) else [],
        scanner_candidate_explosion_regressions=["SCANNER_CANDIDATE_EXPLOSION_REGRESSION"] if any(report.metrics.generated_scanner_candidates > candidate.scanner_threshold_config.scanner_candidate_explosion_guardrail for report in reports for candidate in fixture.candidate_policies) else [],
        blocked_candidate_collapse_regressions=[],
        technical_evidence_missing_regressions=["TECHNICAL_EVIDENCE_MISSING_REGRESSION"] if any(report.metrics.technical_evidence_blocked_count for report in reports) else [],
        profitability_context_missing_regressions=["PROFITABILITY_CONTEXT_MISSING_REGRESSION"] if any(report.metrics.profitability_blocked_count for report in reports) else [],
        compatibility_status_mapping_regressions=["COMPATIBILITY_STATUS_MAPPING_REGRESSION"] if any(
            "evaluation_compatibility_status" not in step.candidate_evaluation_trace
            for report in reports
            for step in report.step_results
        ) else [],
        unsafe_trigger_rejection_regressions=["UNSAFE_TRIGGER_REJECTION_REGRESSION"] if any(report.metrics.unsafe_trigger_rejection_count for report in reports) else [],
    )


def _build_pack(fixture: DomesticCalibrationFixture, single_runs: list[SingleReplayComparisonResult]) -> CalibrationPack:
    coverage = _coverage_report(fixture)
    metrics = _aggregate_pack_metrics(fixture)
    regressions = _regression_report(fixture)
    regression_summaries = (
        regressions.safety_boundary_regressions
        + regressions.domestic_only_regressions
        + regressions.stale_data_policy_regressions
        + regressions.report_only_policy_regressions
        + regressions.scanner_candidate_explosion_regressions
        + regressions.technical_evidence_missing_regressions
        + regressions.profitability_context_missing_regressions
        + regressions.compatibility_status_mapping_regressions
        + regressions.unsafe_trigger_rejection_regressions
    )
    return CalibrationPack(
        calibration_pack_id=f"{fixture.run_id}-pack",
        strategy_track=fixture.calibration_run_config.strategy_track,
        market_profile_summary=fixture.calibration_input_set.market_profile_summary,
        included_single_run_comparison_ids=[item.comparison_result_id for item in single_runs],
        included_replay_report_ids=[report.report_id for report in fixture.calibration_input_set.replay_reports],
        included_scenario_families=sorted(set(fixture.calibration_input_set.scenario_family_labels)),
        included_fixture_families=list(fixture.calibration_input_set.replay_fixture_provenance_markers),
        pack_metrics=metrics,
        pack_coverage_report=coverage,
        regression_summaries=regression_summaries,
        warnings=list(coverage.diversity_warnings),
        block_reasons=list(coverage.missing_scenario_families),
    )


def build_policy_comparison_report(fixture: DomesticCalibrationFixture) -> PolicyComparisonReport:
    single_run_results = [
        _single_run_result(fixture, index, report)
        for index, report in enumerate(fixture.calibration_input_set.replay_reports, start=1)
    ]
    pack = _build_pack(fixture, single_run_results)
    aggregated_candidates = []
    metric_deltas = []
    for candidate in fixture.candidate_policies:
        candidate_summaries = [
            summary
            for single in single_run_results
            for summary in single.candidate_summaries
            if summary.candidate_policy_id == candidate.policy_id
        ]
        coverage_score = sum(item.coverage_score for item in candidate_summaries) // max(len(candidate_summaries), 1)
        aggregated_candidates.append({
            "candidate_policy_id": candidate.policy_id,
            "coverage_score": coverage_score,
            "safety_score": sum(item.safety_score for item in candidate_summaries) // max(len(candidate_summaries), 1),
            "stability_score": sum(item.stability_score for item in candidate_summaries) // max(len(candidate_summaries), 1),
        })
        metric_deltas.append({
            "candidate_policy_id": candidate.policy_id,
            "coverage_score_delta_vs_baseline": coverage_score - 50,
        })
    return PolicyComparisonReport(
        report_id=f"{fixture.run_id}-policy-comparison",
        baseline_policy_id=fixture.baseline_policy.policy_id,
        candidate_policy_ids=[candidate.policy_id for candidate in fixture.candidate_policies],
        single_run_summaries=aggregated_candidates,
        pack_level_summaries={
            "run_count": pack.pack_metrics.runs_evaluated,
            "window_count": pack.pack_metrics.windows_evaluated,
            "coverage_score": pack.pack_metrics.coverage_score,
            "safety_score": pack.pack_metrics.safety_score,
            "stability_score": pack.pack_metrics.stability_score,
        },
        metric_deltas=metric_deltas,
        coverage_summary=pack.pack_coverage_report.model_dump(mode="json"),
        safety_summary={
            "safety_regression_count": pack.pack_metrics.safety_regression_count,
            "unsafe_trigger_rejection_count": pack.pack_metrics.unsafe_trigger_rejection_count,
        },
        stability_summary={"stability_score": pack.pack_metrics.stability_score},
        recommendation_notes=["OFFLINE_DIAGNOSTIC_ONLY"],
        metadata_json=dict(DOMESTIC_CALIBRATION_METADATA),
    )


def build_calibration_run_result(fixture: DomesticCalibrationFixture) -> CalibrationRunResult:
    if fixture.calibration_run_config.strategy_track != StrategyTrack.DOMESTIC_KR:
        raise ValueError("domestic calibration requires StrategyTrack DOMESTIC_KR")
    single_run_results = [
        _single_run_result(fixture, index, report)
        for index, report in enumerate(fixture.calibration_input_set.replay_reports, start=1)
    ]
    pack = _build_pack(fixture, single_run_results)
    comparison_report = build_policy_comparison_report(fixture)
    regression_report = _regression_report(fixture)
    warnings = sorted(set(pack.warnings))
    block_reasons = sorted(set(pack.block_reasons))
    return CalibrationRunResult(
        calibration_run_id=fixture.calibration_run_config.calibration_run_id,
        baseline_policy_summary=fixture.baseline_policy.model_dump(mode="json"),
        candidate_policy_summaries=[candidate.model_dump(mode="json") for candidate in fixture.candidate_policies],
        single_run_results=single_run_results,
        calibration_pack=pack,
        policy_comparison_report=comparison_report,
        regression_report=regression_report,
        warnings=warnings,
        block_reasons=block_reasons,
        metadata_json=dict(DOMESTIC_CALIBRATION_METADATA),
    )


def build_promotion_gate_report(fixture: DomesticCalibrationFixture) -> PromotionGateReport:
    result = build_calibration_run_result(fixture)
    pack = result.calibration_pack
    criteria = fixture.calibration_run_config.promotion_gate_criteria
    status = PromotionGateStatus.PROMOTION_REJECTED
    status_reasons: list[str] = []
    coverage_findings = list(pack.pack_coverage_report.diversity_warnings)
    regression_findings = list(pack.regression_summaries)
    block_reasons = list(pack.block_reasons)
    if pack.pack_metrics.runs_evaluated == 1:
        coverage_findings.append("SINGLE_RUN_ONLY_EVIDENCE")
        block_reasons.append("SINGLE_RUN_ONLY_EVIDENCE")
    if (
        pack.pack_metrics.safety_regression_count > criteria.maximum_safety_regression_count
        or pack.pack_metrics.domestic_only_regression_count > criteria.maximum_domestic_only_regression_count
        or pack.pack_metrics.unsafe_trigger_rejection_count > criteria.maximum_unsafe_trigger_regression_count
    ):
        status = PromotionGateStatus.PROMOTION_BLOCKED_SAFETY
        status_reasons.append("SAFETY_BOUNDARY_REGRESSION")
    elif not pack.pack_coverage_report.coverage_pass or pack.pack_metrics.runs_evaluated < criteria.minimum_calibration_pack_size:
        status = PromotionGateStatus.PROMOTION_BLOCKED_COVERAGE
        status_reasons.append("INSUFFICIENT_CALIBRATION_PACK_COVERAGE")
    elif (
        pack.pack_metrics.stale_data_regression_count > criteria.maximum_stale_data_regression_count
        or pack.pack_metrics.report_only_count > criteria.maximum_report_only_invariant_regression_count
        or pack.pack_metrics.non_actionable_count < 1
        or regression_findings
    ):
        status = PromotionGateStatus.PROMOTION_BLOCKED_REGRESSION
        status_reasons.append("REGRESSION_DETECTED")
    elif pack.pack_metrics.report_only_count:
        status = PromotionGateStatus.PROMOTION_REPORT_ONLY
        status_reasons.append("REPORT_ONLY_INVARIANT_PRESENT")
    elif (
        pack.pack_metrics.coverage_score >= criteria.minimum_coverage_score
        and pack.pack_metrics.safety_score >= criteria.minimum_safety_score
        and pack.pack_metrics.stability_score >= criteria.minimum_stability_score
    ):
        status = PromotionGateStatus.PROMOTION_READY_FOR_PAPER_SHADOW
        status_reasons.append("OFFLINE_EVIDENCE_SUFFICIENT_FOR_FUTURE_SHADOW_DESIGN")
    else:
        status = PromotionGateStatus.PROMOTION_READY_FOR_MORE_REPLAY
        status_reasons.append("MORE_REPLAY_DIVERSITY_REQUIRED")
    return PromotionGateReport(
        report_id=f"{fixture.run_id}-promotion-gate",
        calibration_pack_id=pack.calibration_pack_id,
        gate_status=status,
        status_reasons=status_reasons,
        coverage_findings=sorted(set(coverage_findings)),
        regression_findings=sorted(set(regression_findings)),
        safety_boundary=CalibrationSafetyBoundary(),
        warnings=sorted(set(result.warnings)),
        block_reasons=sorted(set(block_reasons)),
        metadata_json=dict(DOMESTIC_CALIBRATION_METADATA),
    )
