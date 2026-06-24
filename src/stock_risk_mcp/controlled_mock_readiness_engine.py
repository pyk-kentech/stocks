from __future__ import annotations

from stock_risk_mcp.controlled_mock_readiness_guard import validate_controlled_mock_readiness_metadata_safety
from stock_risk_mcp.controlled_mock_readiness_models import (
    ControlledMockReadinessDecision,
    ControlledMockReadinessGapCategory,
    ControlledMockReadinessGapEntry,
    ControlledMockReadinessGapReport,
    ControlledMockReadinessInput,
    ControlledMockReadinessSummaryReport,
    MockBoundaryViolationReport,
    MockInfrastructureReadinessReport,
    MockReadinessDependencyReport,
    MockSafetyPolicyReport,
    PaperPassEvidenceReport,
)


def _gap(input_id: str, suffix: str, category, severity: str, message: str) -> ControlledMockReadinessGapEntry:
    return ControlledMockReadinessGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def build_controlled_mock_readiness_review(
    review_input: ControlledMockReadinessInput,
) -> ControlledMockReadinessInput:
    for audit in review_input.audit_records:
        validate_controlled_mock_readiness_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="controlled mock readiness",
        )

    gaps: list[ControlledMockReadinessGapEntry] = []
    if not review_input.paper_evaluation_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-V77", ControlledMockReadinessGapCategory.MISSING_V77_PAPER_EVAL, "WARNING", "paper evaluation ref is missing"))
    if review_input.paper_evaluation_decision != "PAPER_PASS":
        severity = "BLOCKING" if review_input.paper_evaluation_decision in {"BLOCKED", "REJECTED"} else "WARNING"
        gaps.append(_gap(review_input.readiness_review_id, "INVALID-PAPER-EVAL", ControlledMockReadinessGapCategory.INVALID_PAPER_EVAL_DECISION, severity, "paper evaluation decision is not PAPER_PASS"))
    if not review_input.allocation_policy_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-V76", ControlledMockReadinessGapCategory.MISSING_V76_POLICY, "WARNING", "allocation policy ref is missing"))
    if review_input.allocation_policy_decision not in {"PAPER_CANDIDATE", "TRAINED_OFFLINE"}:
        gaps.append(_gap(review_input.readiness_review_id, "INVALID-V76", ControlledMockReadinessGapCategory.INVALID_V76_POLICY_DECISION, "WARNING", "allocation policy decision is not mock-review compatible"))
    if not review_input.strategy_ensemble_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-ENSEMBLE", ControlledMockReadinessGapCategory.MISSING_ENSEMBLE_DEPENDENCY, "WARNING", "strategy ensemble dependency is missing"))
    if not review_input.risk_control_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-RISK", ControlledMockReadinessGapCategory.MISSING_RISK_CONTROL, "WARNING", "risk control ref is missing"))
    if not review_input.mock_oauth_readiness_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-OAUTH", ControlledMockReadinessGapCategory.MISSING_OAUTH_READINESS, "WARNING", "mock oauth readiness ref is missing"))
    if not review_input.mock_market_data_readiness_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-MARKET-DATA", ControlledMockReadinessGapCategory.MISSING_MARKET_DATA_READINESS, "WARNING", "mock market data readiness ref is missing"))
    if not review_input.broker_adapter_boundary_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-BROKER-BOUNDARY", ControlledMockReadinessGapCategory.MISSING_BROKER_ADAPTER_BOUNDARY, "WARNING", "broker adapter boundary ref is missing"))
    if not review_input.order_gate_boundary_ref:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-ORDER-GATE", ControlledMockReadinessGapCategory.MISSING_ORDER_GATE_BOUNDARY, "WARNING", "order gate boundary ref is missing"))
    if not review_input.kill_switch_policy_ref or not review_input.safety_policy.kill_switch_policy_present:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-KILL-SWITCH", ControlledMockReadinessGapCategory.MISSING_KILL_SWITCH, "BLOCKING", "kill switch policy is missing"))
    if not review_input.user_opt_in_policy_ref or not review_input.safety_policy.explicit_user_opt_in_required:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-OPT-IN", ControlledMockReadinessGapCategory.MISSING_USER_OPT_IN_POLICY, "BLOCKING", "explicit user opt-in policy is missing"))
    if not review_input.audit_policy_ref or not review_input.safety_policy.audit_requirement_present:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-AUDIT", ControlledMockReadinessGapCategory.MISSING_AUDIT_POLICY, "WARNING", "audit policy is missing"))
    if not review_input.rollback_policy_ref or not review_input.safety_policy.rollback_requirement_present:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-ROLLBACK", ControlledMockReadinessGapCategory.MISSING_ROLLBACK_POLICY, "WARNING", "rollback policy is missing"))
    if not review_input.costs_present:
        gaps.append(_gap(review_input.readiness_review_id, "MISSING-COSTS", ControlledMockReadinessGapCategory.MISSING_COST_SLIPPAGE_EVIDENCE, "WARNING", "cost/slippage evidence is missing"))
    if review_input.cnn_feature_gap_noted:
        gaps.append(_gap(review_input.readiness_review_id, "CNN-FEATURE-GAP", ControlledMockReadinessGapCategory.CNN_FEATURE_GAP_NOTED, "REPORT_ONLY", "cnn fear and greed feature gap noted"))
    if not review_input.drawdown_limit_passed:
        gaps.append(_gap(review_input.readiness_review_id, "EXCESSIVE-DRAWDOWN", ControlledMockReadinessGapCategory.EXCESSIVE_DRAWDOWN, "BLOCKING", "drawdown limit did not pass"))
    if not review_input.exposure_limit_passed:
        gaps.append(_gap(review_input.readiness_review_id, "EXCESSIVE-EXPOSURE", ControlledMockReadinessGapCategory.EXCESSIVE_EXPOSURE, "BLOCKING", "exposure limit did not pass"))
    if not review_input.turnover_limit_passed:
        gaps.append(_gap(review_input.readiness_review_id, "EXCESSIVE-TURNOVER", ControlledMockReadinessGapCategory.EXCESSIVE_TURNOVER, "WARNING", "turnover limit did not pass"))
    if review_input.live_prod_path_attempt:
        gaps.append(_gap(review_input.readiness_review_id, "LIVE-PROD", ControlledMockReadinessGapCategory.LIVE_PROD_PATH_ATTEMPT, "BLOCKING", "live/prod path attempt detected"))
    if review_input.real_broker_dependency:
        gaps.append(_gap(review_input.readiness_review_id, "REAL-BROKER", ControlledMockReadinessGapCategory.REAL_BROKER_DEPENDENCY, "BLOCKING", "real broker dependency detected"))
    if review_input.real_account_dependency:
        gaps.append(_gap(review_input.readiness_review_id, "REAL-ACCOUNT", ControlledMockReadinessGapCategory.REAL_ACCOUNT_DEPENDENCY, "BLOCKING", "real account dependency detected"))
    if review_input.real_order_dependency:
        gaps.append(_gap(review_input.readiness_review_id, "REAL-ORDER", ControlledMockReadinessGapCategory.REAL_ORDER_DEPENDENCY, "BLOCKING", "real order dependency detected"))
    if review_input.websocket_dependency:
        gaps.append(_gap(review_input.readiness_review_id, "WEBSOCKET", ControlledMockReadinessGapCategory.WEBSOCKET_DEPENDENCY, "BLOCKING", "websocket dependency detected"))
    if review_input.autonomous_execution_path:
        gaps.append(_gap(review_input.readiness_review_id, "AUTONOMOUS", ControlledMockReadinessGapCategory.AUTONOMOUS_EXECUTION_PATH, "BLOCKING", "autonomous execution path detected"))

    if any(entry.severity == "BLOCKING" for entry in gaps):
        decision = ControlledMockReadinessDecision.BLOCKED
        reason = "blocking mock-readiness gaps detected"
    elif any(entry.gap_category in {
        ControlledMockReadinessGapCategory.MISSING_V77_PAPER_EVAL,
        ControlledMockReadinessGapCategory.MISSING_V76_POLICY,
        ControlledMockReadinessGapCategory.MISSING_ENSEMBLE_DEPENDENCY,
        ControlledMockReadinessGapCategory.MISSING_RISK_CONTROL,
        ControlledMockReadinessGapCategory.MISSING_OAUTH_READINESS,
        ControlledMockReadinessGapCategory.MISSING_MARKET_DATA_READINESS,
        ControlledMockReadinessGapCategory.MISSING_BROKER_ADAPTER_BOUNDARY,
        ControlledMockReadinessGapCategory.MISSING_ORDER_GATE_BOUNDARY,
        ControlledMockReadinessGapCategory.MISSING_AUDIT_POLICY,
        ControlledMockReadinessGapCategory.MISSING_ROLLBACK_POLICY,
    } for entry in gaps):
        decision = ControlledMockReadinessDecision.GAP
        reason = "required evidence is missing"
    elif review_input.paper_evaluation_decision != "PAPER_PASS":
        decision = ControlledMockReadinessDecision.RESEARCH_ONLY
        reason = "paper evaluation is not pass-ready"
    elif review_input.mock_oauth_readiness_status == "AVAILABLE" and review_input.mock_market_data_readiness_status == "AVAILABLE":
        decision = ControlledMockReadinessDecision.MOCK_DRY_RUN_READY
        reason = "paper pass and mock infrastructure evidence are complete"
    else:
        decision = ControlledMockReadinessDecision.MOCK_REVIEW_READY
        reason = "paper pass is present and mock review can proceed"

    summary = ControlledMockReadinessSummaryReport(
        report_id=f"{review_input.readiness_review_id}-SUMMARY-REPORT",
        decision=decision,
        decision_reason=reason,
    )
    dependency = MockReadinessDependencyReport(
        report_id=f"{review_input.readiness_review_id}-DEPENDENCY-REPORT",
        paper_eval_decision=review_input.paper_evaluation_decision or "MISSING",
        policy_decision=review_input.allocation_policy_decision or "MISSING",
        ensemble_dependency_present=bool(review_input.strategy_ensemble_ref),
        point_in_time_evidence_present=review_input.point_in_time_evidence_present,
        walk_forward_evidence_present=review_input.walk_forward_evidence_present,
        costs_present=review_input.costs_present,
        cnn_feature_gap_noted=review_input.cnn_feature_gap_noted,
    )
    evidence = PaperPassEvidenceReport(
        report_id=f"{review_input.readiness_review_id}-PAPER-PASS-EVIDENCE-REPORT",
        paper_eval_passed=review_input.paper_evaluation_decision == "PAPER_PASS",
        drawdown_limit_passed=review_input.drawdown_limit_passed,
        exposure_limit_passed=review_input.exposure_limit_passed,
        turnover_limit_passed=review_input.turnover_limit_passed,
        costs_present=review_input.costs_present,
    )
    infrastructure = MockInfrastructureReadinessReport(
        report_id=f"{review_input.readiness_review_id}-INFRASTRUCTURE-REPORT",
        mock_oauth_status=review_input.mock_oauth_readiness_status or "GAP",
        mock_market_data_status=review_input.mock_market_data_readiness_status or "GAP",
        broker_adapter_boundary_present=bool(review_input.broker_adapter_boundary_ref),
        order_gate_boundary_present=bool(review_input.order_gate_boundary_ref),
    )
    safety_policy_report = MockSafetyPolicyReport(
        report_id=f"{review_input.readiness_review_id}-SAFETY-POLICY-REPORT",
        policy=review_input.safety_policy,
    )
    boundary = MockBoundaryViolationReport(
        report_id=f"{review_input.readiness_review_id}-BOUNDARY-VIOLATION-REPORT",
        live_prod_path_attempt=review_input.live_prod_path_attempt,
        real_broker_dependency=review_input.real_broker_dependency,
        real_account_dependency=review_input.real_account_dependency,
        real_order_dependency=review_input.real_order_dependency,
        websocket_dependency=review_input.websocket_dependency,
        autonomous_execution_path=review_input.autonomous_execution_path,
        missing_kill_switch=not bool(review_input.kill_switch_policy_ref),
        missing_opt_in_policy=not bool(review_input.user_opt_in_policy_ref),
        missing_audit_trail=not bool(review_input.audit_policy_ref),
        missing_rollback_policy=not bool(review_input.rollback_policy_ref),
    )
    gaps.append(_gap(review_input.readiness_review_id, "REPORT-GENERATED", ControlledMockReadinessGapCategory.READINESS_REPORT_GENERATED, "REPORT_ONLY", "controlled mock readiness report generated"))
    gap_report = ControlledMockReadinessGapReport(
        gap_report_id=f"{review_input.readiness_review_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gaps,
        blocking_gap_count=sum(1 for item in gaps if item.severity == "BLOCKING"),
        warning_gap_count=sum(1 for item in gaps if item.severity == "WARNING"),
    )
    return review_input.model_copy(update={
        "summary_report": summary,
        "dependency_report": dependency,
        "paper_pass_evidence_report": evidence,
        "infrastructure_readiness_report": infrastructure,
        "safety_policy_report": safety_policy_report,
        "boundary_violation_report": boundary,
        "gap_report": gap_report,
    })
