from __future__ import annotations

from stock_risk_mcp.point_in_time_universe_guard import (
    validate_point_in_time_universe_metadata_safety,
)
from stock_risk_mcp.point_in_time_universe_models import (
    DatasetLeakageReport,
    DatasetPromotionReadinessReport,
    PointInTimeUniverseDecision,
    PointInTimeUniverseGapCategory,
    PointInTimeUniverseGapEntry,
    PointInTimeUniverseGapReport,
    PointInTimeUniverseInput,
    PointInTimeUniverseReport,
    PointInTimeUniverseSafetyReport,
    PointInTimeUniverseSource,
    SecurityLifecycleCoverageReport,
    SecurityLifecycleStatus,
    SurvivorshipBiasDatasetReport,
)


def build_point_in_time_universe_gate(
    universe_input: PointInTimeUniverseInput,
) -> PointInTimeUniverseInput:
    gap_entries: list[PointInTimeUniverseGapEntry] = []
    for audit in universe_input.audit_records:
        validate_point_in_time_universe_metadata_safety(
            {
                "operator_context": audit.operator_context,
                "source_path": audit.source_path,
            },
            context="point in time universe",
        )

    snapshot_coverage_complete = bool(universe_input.universe_snapshots)
    available_at_complete = universe_input.available_at_coverage_complete and all(
        snapshot.available_at is not None for snapshot in universe_input.universe_snapshots
    )
    tradability_complete = universe_input.tradability_coverage_complete and all(
        bool(snapshot.tradability_status) for snapshot in universe_input.universe_snapshots
    )
    point_in_time_report = PointInTimeUniverseReport(
        report_id=f"{universe_input.input_id}-POINT-IN-TIME-UNIVERSE-REPORT",
        universe_source=universe_input.universe_source,
        available_at_complete=available_at_complete,
        snapshot_coverage_complete=snapshot_coverage_complete,
        tradability_coverage_complete=tradability_complete,
    )

    current_survivors_only = universe_input.universe_source == PointInTimeUniverseSource.CURRENT_SURVIVORS_ONLY
    training_grade_allowed = universe_input.universe_source == PointInTimeUniverseSource.POINT_IN_TIME_UNIVERSE
    survivorship_findings: list[str] = []
    if current_survivors_only:
        survivorship_findings.append("current survivors only source")
        training_grade_allowed = False
        gap_entries.append(_gap(universe_input, "CURRENT-SURVIVORS-ONLY", PointInTimeUniverseGapCategory.CURRENT_SURVIVORS_ONLY_TRAINING_BLOCKED, "BLOCKING", "current survivors only dataset cannot be training-grade"))
    elif universe_input.universe_source == PointInTimeUniverseSource.MIXED_OR_UNKNOWN:
        survivorship_findings.append("mixed or unknown universe source")
        training_grade_allowed = False
        gap_entries.append(_gap(universe_input, "MIXED-OR-UNKNOWN", PointInTimeUniverseGapCategory.MIXED_OR_UNKNOWN_SOURCE, "WARNING", "mixed or unknown universe source"))
    elif universe_input.universe_source == PointInTimeUniverseSource.INVALID:
        training_grade_allowed = False
        gap_entries.append(_gap(universe_input, "INVALID-SOURCE", PointInTimeUniverseGapCategory.INVALID_SOURCE, "BLOCKING", "invalid universe source"))
    survivorship_report = SurvivorshipBiasDatasetReport(
        report_id=f"{universe_input.input_id}-SURVIVORSHIP-BIAS-REPORT",
        current_survivors_only=current_survivors_only,
        training_grade_allowed=training_grade_allowed,
        findings=survivorship_findings,
    )

    lifecycle_statuses = {record.status for record in universe_input.security_lifecycle_records}
    delisting_complete = SecurityLifecycleStatus.DELISTED in lifecycle_statuses
    suspension_complete = SecurityLifecycleStatus.SUSPENDED in lifecycle_statuses
    rename_complete = SecurityLifecycleStatus.RENAMED in lifecycle_statuses
    lifecycle_report = SecurityLifecycleCoverageReport(
        report_id=f"{universe_input.input_id}-SECURITY-LIFECYCLE-COVERAGE-REPORT",
        lifecycle_statuses_present=sorted(lifecycle_statuses, key=lambda item: item.value),
        delisting_coverage_complete=delisting_complete,
        suspension_coverage_complete=suspension_complete,
        rename_coverage_complete=rename_complete,
        corporate_action_coverage_complete=universe_input.corporate_action_coverage_complete,
        index_membership_coverage_complete=universe_input.index_membership_coverage_complete,
    )

    leakage_report = DatasetLeakageReport(
        report_id=f"{universe_input.input_id}-DATASET-LEAKAGE-REPORT",
        future_index_membership_leakage_detected=universe_input.future_index_membership_leakage_detected,
        current_constituent_replay_leakage_detected=universe_input.current_constituent_replay_leakage_detected,
        future_delisting_knowledge_leakage_detected=universe_input.future_delisting_knowledge_leakage_detected,
        symbol_survivorship_leakage_detected=universe_input.symbol_survivorship_leakage_detected,
        missing_available_at_detected=not available_at_complete,
    )

    if not available_at_complete:
        gap_entries.append(_gap(universe_input, "AVAILABLE-AT-MISSING", PointInTimeUniverseGapCategory.AVAILABLE_AT_MISSING, "WARNING", "available_at coverage is incomplete"))
    if not delisting_complete:
        gap_entries.append(_gap(universe_input, "DELISTING-COVERAGE-MISSING", PointInTimeUniverseGapCategory.DELISTING_COVERAGE_MISSING, "WARNING", "delisting coverage missing"))
    if not suspension_complete:
        gap_entries.append(_gap(universe_input, "SUSPENSION-COVERAGE-MISSING", PointInTimeUniverseGapCategory.SUSPENSION_COVERAGE_MISSING, "WARNING", "suspension coverage missing"))
    if not rename_complete:
        gap_entries.append(_gap(universe_input, "RENAME-COVERAGE-MISSING", PointInTimeUniverseGapCategory.RENAME_COVERAGE_MISSING, "WARNING", "rename coverage missing"))
    if not universe_input.corporate_action_coverage_complete:
        gap_entries.append(_gap(universe_input, "CORPORATE-ACTION-COVERAGE-MISSING", PointInTimeUniverseGapCategory.CORPORATE_ACTION_COVERAGE_MISSING, "WARNING", "corporate action coverage missing"))
    if not universe_input.index_membership_coverage_complete:
        gap_entries.append(_gap(universe_input, "INDEX-MEMBERSHIP-COVERAGE-MISSING", PointInTimeUniverseGapCategory.INDEX_MEMBERSHIP_COVERAGE_MISSING, "WARNING", "index membership coverage missing"))
    if not tradability_complete:
        gap_entries.append(_gap(universe_input, "TRADABILITY-COVERAGE-MISSING", PointInTimeUniverseGapCategory.TRADABILITY_COVERAGE_MISSING, "WARNING", "tradability coverage missing"))
    if not universe_input.missing_date_gap_coverage_complete:
        gap_entries.append(_gap(universe_input, "MISSING-DATE-GAP-COVERAGE", PointInTimeUniverseGapCategory.MISSING_DATE_GAP_COVERAGE, "WARNING", "missing date gap coverage incomplete"))
    if universe_input.future_index_membership_leakage_detected:
        gap_entries.append(_gap(universe_input, "FUTURE-INDEX-MEMBERSHIP-LEAKAGE", PointInTimeUniverseGapCategory.FUTURE_INDEX_MEMBERSHIP_LEAKAGE, "BLOCKING", "future index membership leakage detected"))
    if universe_input.current_constituent_replay_leakage_detected:
        gap_entries.append(_gap(universe_input, "CURRENT-CONSTITUENT-REPLAY-LEAKAGE", PointInTimeUniverseGapCategory.CURRENT_CONSTITUENT_REPLAY_LEAKAGE, "BLOCKING", "current constituent replay leakage detected"))
    if universe_input.future_delisting_knowledge_leakage_detected:
        gap_entries.append(_gap(universe_input, "FUTURE-DELISTING-KNOWLEDGE-LEAKAGE", PointInTimeUniverseGapCategory.FUTURE_DELISTING_KNOWLEDGE_LEAKAGE, "BLOCKING", "future delisting knowledge leakage detected"))
    if universe_input.symbol_survivorship_leakage_detected:
        gap_entries.append(_gap(universe_input, "SYMBOL-SURVIVORSHIP-LEAKAGE", PointInTimeUniverseGapCategory.SYMBOL_SURVIVORSHIP_LEAKAGE, "BLOCKING", "symbol survivorship leakage detected"))

    safety_report = PointInTimeUniverseSafetyReport(
        safety_report_id=f"{universe_input.input_id}-SAFETY-REPORT",
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
        universe_input=universe_input,
        training_grade_allowed=training_grade_allowed,
        available_at_complete=available_at_complete,
        delisting_complete=delisting_complete,
        suspension_complete=suspension_complete,
        rename_complete=rename_complete,
        tradability_complete=tradability_complete,
        gap_entries=gap_entries,
    )
    readiness_report = DatasetPromotionReadinessReport(
        report_id=f"{universe_input.input_id}-DATASET-PROMOTION-READINESS-REPORT",
        decision=decision,
        decision_reason=reason,
        training_grade_candidate=decision == PointInTimeUniverseDecision.TRAINING_READY,
    )
    gap_entries.append(_gap(universe_input, "POINT-IN-TIME-UNIVERSE-REPORT-GENERATED", PointInTimeUniverseGapCategory.POINT_IN_TIME_UNIVERSE_REPORT_GENERATED, "REPORT_ONLY", "point in time universe report generated"))
    gap_report = PointInTimeUniverseGapReport(
        gap_report_id=f"{universe_input.input_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gap_entries,
        blocking_gap_count=sum(1 for item in gap_entries if item.severity == "BLOCKING"),
        warning_gap_count=sum(1 for item in gap_entries if item.severity == "WARNING"),
    )
    return universe_input.model_copy(
        update={
            "point_in_time_universe_report": point_in_time_report,
            "survivorship_bias_report": survivorship_report,
            "security_lifecycle_coverage_report": lifecycle_report,
            "leakage_report": leakage_report,
            "dataset_promotion_readiness_report": readiness_report,
            "gap_report": gap_report,
            "safety_report": safety_report,
        }
    )


def _decide(*, universe_input, training_grade_allowed, available_at_complete, delisting_complete, suspension_complete, rename_complete, tradability_complete, gap_entries):
    blocking = [entry for entry in gap_entries if entry.severity == "BLOCKING"]
    warnings = [entry for entry in gap_entries if entry.severity == "WARNING"]
    if universe_input.universe_source == PointInTimeUniverseSource.INVALID:
        return PointInTimeUniverseDecision.REJECTED, "invalid universe source"
    if blocking:
        return PointInTimeUniverseDecision.BLOCKED, blocking[0].message
    if universe_input.universe_source == PointInTimeUniverseSource.CURRENT_SURVIVORS_ONLY:
        return PointInTimeUniverseDecision.RESEARCH_ONLY, "current survivors only source is research-only"
    if universe_input.universe_source == PointInTimeUniverseSource.MIXED_OR_UNKNOWN:
        return PointInTimeUniverseDecision.GAP, "mixed or unknown universe source"
    training_ready = all(
        (
            training_grade_allowed,
            available_at_complete,
            delisting_complete,
            suspension_complete,
            rename_complete,
            universe_input.corporate_action_coverage_complete,
            universe_input.index_membership_coverage_complete,
            tradability_complete,
            universe_input.missing_date_gap_coverage_complete,
        )
    )
    if training_ready:
        return PointInTimeUniverseDecision.TRAINING_READY, "point-in-time universe evidence is sufficient"
    if warnings:
        return PointInTimeUniverseDecision.GAP, warnings[0].message
    return PointInTimeUniverseDecision.RESEARCH_ONLY, "local offline universe gate is available for research only"


def _gap(universe_input, suffix, category, severity, message):
    return PointInTimeUniverseGapEntry(
        gap_id=f"{universe_input.input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )
