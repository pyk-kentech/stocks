from __future__ import annotations

from stock_risk_mcp.controlled_mock_dry_run_guard import validate_controlled_mock_dry_run_metadata_safety
from stock_risk_mcp.controlled_mock_dry_run_models import (
    ControlledMockDryRunDecision,
    ControlledMockDryRunGapEntry,
    ControlledMockDryRunGapReport,
    ControlledMockDryRunInput,
    ControlledMockDryRunSummaryReport,
    MockBoundaryViolationReport,
    MockIntentRouteType,
    MockOrderIntentPreview,
    SimpleStatusReport,
)


def _gap(input_id: str, suffix: str, category: str, severity: str, message: str) -> ControlledMockDryRunGapEntry:
    return ControlledMockDryRunGapEntry(
        gap_id=f"{input_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _present(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _status_report(report_id: str, status: str, passed: bool, details: list[str] | None = None) -> SimpleStatusReport:
    return SimpleStatusReport(report_id=report_id, status=status, passed=passed, details=details or [])


def build_controlled_mock_dry_run_review(review_input: ControlledMockDryRunInput) -> ControlledMockDryRunInput:
    for audit in review_input.audit_records:
        validate_controlled_mock_dry_run_metadata_safety(
            {"source_path": audit.source_path, "operator_context": audit.operator_context},
            context="controlled mock dry run audit",
        )
    for ref in review_input.source_refs:
        validate_controlled_mock_dry_run_metadata_safety({"source_ref": ref}, context="controlled mock dry run ref")

    gaps: list[ControlledMockDryRunGapEntry] = []
    warnings: list[str] = []
    blocked_findings: list[str] = []

    if not _present(review_input.paper_evaluation_ref) or not _present(review_input.mock_readiness_ref):
        gaps.append(_gap(review_input.dry_run_id, "MISSING-UPSTREAM", "MISSING_V77_OR_V78_DEPENDENCY", "WARNING", "v7.7 or v7.8 dependency is missing"))
    if review_input.paper_evaluation_decision != "PAPER_PASS":
        gaps.append(_gap(review_input.dry_run_id, "PAPER-PASS", "FAILED_PAPER_PASS", "BLOCKING", "paper evaluation must be PAPER_PASS"))

    for ref_name, ref_value in (
        ("STRATEGY_ENSEMBLE_REF", review_input.strategy_ensemble_ref),
        ("RISK_POLICY_REF", review_input.risk_policy_ref),
        ("ORDER_GATE_BOUNDARY_REF", review_input.order_gate_boundary_ref),
        ("MOCK_MARKET_DATA_READINESS_REF", review_input.mock_market_data_readiness_ref),
        ("MOCK_OAUTH_READINESS_REF", review_input.mock_oauth_readiness_ref),
    ):
        if not _present(ref_value):
            gaps.append(_gap(review_input.dry_run_id, ref_name, f"MISSING_{ref_name}", "WARNING", f"{ref_name.lower()} is missing"))

    if not _present(review_input.opt_in_policy_ref):
        gaps.append(_gap(review_input.dry_run_id, "MISSING-OPT-IN", "MISSING_OPT_IN_POLICY", "BLOCKING", "opt-in policy is missing"))
    if not _present(review_input.kill_switch_policy_ref):
        gaps.append(_gap(review_input.dry_run_id, "MISSING-KILL-SWITCH", "MISSING_KILL_SWITCH_POLICY", "BLOCKING", "kill switch policy is missing"))
    if not _present(review_input.rollback_policy_ref):
        gaps.append(_gap(review_input.dry_run_id, "MISSING-ROLLBACK", "MISSING_ROLLBACK_POLICY", "WARNING", "rollback policy is missing"))
    if not _present(review_input.audit_policy_ref):
        gaps.append(_gap(review_input.dry_run_id, "MISSING-AUDIT", "MISSING_AUDIT_POLICY", "WARNING", "audit policy is missing"))

    if review_input.live_prod_path_attempt:
        gaps.append(_gap(review_input.dry_run_id, "LIVE-PROD", "LIVE_PROD_PATH_BLOCKED", "BLOCKING", "live/prod path detected"))
    if review_input.real_broker_dependency:
        gaps.append(_gap(review_input.dry_run_id, "REAL-BROKER", "REAL_BROKER_DEPENDENCY_BLOCKED", "BLOCKING", "real broker dependency detected"))
    if review_input.kiwoom_dependency:
        gaps.append(_gap(review_input.dry_run_id, "KIWOOM", "KIWOOM_DEPENDENCY_BLOCKED", "BLOCKING", "kiwoom dependency detected"))
    if review_input.kiwoom_mock_order_execution_dependency:
        gaps.append(_gap(review_input.dry_run_id, "KIWOOM-MOCK-ORDER", "KIWOOM_MOCK_ORDER_EXECUTION_BLOCKED", "BLOCKING", "kiwoom mock order execution dependency detected"))
    if review_input.provider_network_dependency:
        gaps.append(_gap(review_input.dry_run_id, "PROVIDER-NETWORK", "PROVIDER_NETWORK_DEPENDENCY_BLOCKED", "BLOCKING", "provider or network dependency detected"))
    if review_input.websocket_dependency:
        gaps.append(_gap(review_input.dry_run_id, "WEBSOCKET", "WEBSOCKET_DEPENDENCY_BLOCKED", "BLOCKING", "websocket dependency detected"))
    if review_input.autonomous_execution_path:
        gaps.append(_gap(review_input.dry_run_id, "AUTONOMOUS", "AUTONOMOUS_EXECUTION_PATH_BLOCKED", "BLOCKING", "autonomous execution path detected"))
    if review_input.executable_order_object_present:
        gaps.append(_gap(review_input.dry_run_id, "EXECUTABLE-ORDER", "EXECUTABLE_ORDER_OBJECT_BLOCKED", "BLOCKING", "executable order object detected"))
    if review_input.real_order_id_present:
        gaps.append(_gap(review_input.dry_run_id, "REAL-ORDER-ID", "REAL_ORDER_ID_BLOCKED", "BLOCKING", "real order id detected"))
    if review_input.raw_account_output_present:
        gaps.append(_gap(review_input.dry_run_id, "RAW-ACCOUNT", "RAW_ACCOUNT_OUTPUT_BLOCKED", "BLOCKING", "raw account output detected"))
    if review_input.credential_token_output_present:
        gaps.append(_gap(review_input.dry_run_id, "TOKEN-OUTPUT", "TOKEN_OUTPUT_BLOCKED", "BLOCKING", "credential or token output detected"))
    if review_input.missing_fail_closed_behavior:
        gaps.append(_gap(review_input.dry_run_id, "FAIL-CLOSED", "MISSING_FAIL_CLOSED_BEHAVIOR", "BLOCKING", "fail-closed behavior is missing"))

    if review_input.position_sizing_decision in {"BLOCKED", "DATA_GAP", "GAP", "REJECTED"}:
        gaps.append(_gap(review_input.dry_run_id, "POSITION-SIZING", "POSITION_SIZING_BLOCKED", "BLOCKING", "position sizing blocks dry-run readiness"))
    if review_input.event_risk_decision in {"BLOCK_NEW_ENTRY", "BLOCKED", "DATA_GAP", "REJECTED"}:
        gaps.append(_gap(review_input.dry_run_id, "EVENT-RISK", "EVENT_RISK_BLOCKED", "BLOCKING", "event risk blocks dry-run readiness"))

    reduce_only_mode = review_input.event_risk_decision == "REDUCE_ONLY"
    if reduce_only_mode and not review_input.candidate_is_exposure_reducing:
        gaps.append(_gap(review_input.dry_run_id, "REDUCE-ONLY", "EVENT_RISK_REDUCE_ONLY_NOT_COMPATIBLE", "BLOCKING", "event risk reduce-only allows exposure reduction only"))

    if review_input.current_order_count > review_input.max_order_count_limit:
        gaps.append(_gap(review_input.dry_run_id, "ORDER-COUNT", "ORDER_COUNT_LIMIT_EXCEEDED", "BLOCKING", "order count limit exceeded"))
    if review_input.projected_total_exposure > review_input.max_total_exposure:
        gaps.append(_gap(review_input.dry_run_id, "EXPOSURE", "TOTAL_EXPOSURE_LIMIT_EXCEEDED", "BLOCKING", "total exposure limit exceeded"))
    if review_input.candidate_is_inverse_or_hedge and review_input.projected_inverse_hedge_exposure > review_input.max_inverse_hedge_exposure:
        gaps.append(_gap(review_input.dry_run_id, "INVERSE-EXPOSURE", "INVERSE_HEDGE_EXPOSURE_LIMIT_EXCEEDED", "BLOCKING", "inverse hedge exposure limit exceeded"))

    breadth_route = review_input.breadth_routing_decision or "WATCH_NON_LEADERS"
    route_type = MockIntentRouteType.CORE_STRATEGY
    if breadth_route == "LEADERSHIP_ONLY":
        route_type = MockIntentRouteType.LEADERSHIP_ONLY
        if not review_input.candidate_is_leadership:
            gaps.append(_gap(review_input.dry_run_id, "LEADERSHIP-ONLY", "NON_LEADERSHIP_CANDIDATE_BLOCKED", "BLOCKING", "non-leadership candidate cannot pass leadership-only route"))
    elif breadth_route == "SECTOR_ONLY":
        route_type = MockIntentRouteType.SECTOR_ONLY
        if not review_input.candidate_is_leadership:
            gaps.append(_gap(review_input.dry_run_id, "SECTOR-ONLY", "NON_LEADERSHIP_CANDIDATE_BLOCKED", "BLOCKING", "non-leadership candidate cannot pass sector-only route"))
    elif breadth_route == "LARGE_CAP_ONLY":
        route_type = MockIntentRouteType.LARGE_CAP_ONLY
    elif breadth_route == "WATCH_NON_LEADERS":
        route_type = MockIntentRouteType.WATCH_ONLY
        gaps.append(_gap(review_input.dry_run_id, "WATCH-NON-LEADERS", "WATCH_NON_LEADERS_BLOCKED", "WARNING", "watch non-leaders prevents promotion"))
    elif breadth_route == "BLOCK_CHASING":
        route_type = MockIntentRouteType.BLOCKED
        gaps.append(_gap(review_input.dry_run_id, "BLOCK-CHASING", "BLOCK_CHASING_ROUTE", "BLOCKING", "crowded leadership chase is blocked"))
    elif breadth_route == "OUTLIER_MOMENTUM_ALLOWED":
        route_type = MockIntentRouteType.OUTLIER_MOMENTUM_SLEEVE
        if not review_input.candidate_is_outlier:
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-ROUTE", "OUTLIER_ROUTE_MISMATCH", "BLOCKING", "non-outlier candidate cannot use outlier sleeve"))
    elif breadth_route == "OUTLIER_MOMENTUM_RESTRICTED":
        route_type = MockIntentRouteType.OUTLIER_MOMENTUM_SLEEVE
        warnings.append("OUTLIER_RESTRICTED")
    elif breadth_route == "BROAD_MARKET_OK":
        route_type = MockIntentRouteType.CORE_STRATEGY

    if review_input.candidate_is_outlier:
        if not _present(review_input.stop_discipline_ref):
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-STOP", "OUTLIER_STOP_DISCIPLINE_MISSING", "WARNING", "outlier sleeve requires stop discipline"))
        if not _present(review_input.liquidity_evidence_ref):
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-LIQUIDITY", "OUTLIER_LIQUIDITY_EVIDENCE_MISSING", "WARNING", "outlier sleeve requires liquidity evidence"))
        if not _present(review_input.slippage_risk_note):
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-SLIPPAGE", "OUTLIER_SLIPPAGE_NOTE_MISSING", "WARNING", "outlier sleeve requires slippage risk note"))
        if review_input.outlier_max_sleeve_allocation is not None and review_input.candidate_requested_sleeve_allocation > review_input.outlier_max_sleeve_allocation:
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-SLEEVE", "OUTLIER_SLEEVE_MAX_ALLOCATION_EXCEEDED", "BLOCKING", "outlier sleeve allocation exceeds cap"))
        if review_input.outlier_max_per_name_risk is not None and review_input.candidate_requested_per_name_risk > review_input.outlier_max_per_name_risk:
            gaps.append(_gap(review_input.dry_run_id, "OUTLIER-RISK", "OUTLIER_PER_NAME_RISK_EXCEEDED", "BLOCKING", "outlier per-name risk exceeds cap"))

    if review_input.mock_readiness_decision == "MOCK_REVIEW_READY":
        base_ready = ControlledMockDryRunDecision.DRY_RUN_REHEARSED
    elif review_input.mock_readiness_decision == "MOCK_DRY_RUN_READY":
        base_ready = ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY
    elif review_input.mock_readiness_decision in {"BLOCKED", "GAP", "REJECTED"}:
        base_ready = ControlledMockDryRunDecision.BLOCKED
    else:
        base_ready = ControlledMockDryRunDecision.RESEARCH_ONLY

    if any(entry.severity == "BLOCKING" for entry in gaps):
        decision = ControlledMockDryRunDecision.BLOCKED
        reason = "blocking dry-run rehearsal gap detected"
    elif any(entry.severity == "WARNING" for entry in gaps):
        if route_type == MockIntentRouteType.WATCH_ONLY:
            decision = ControlledMockDryRunDecision.WATCH_ONLY
            reason = "watch-only route prevents promotion"
        else:
            decision = ControlledMockDryRunDecision.GAP
            reason = "dry-run evidence is incomplete"
    else:
        decision = base_ready
        reason = (
            "complete dry-run rehearsal is eligible for later execution review"
            if decision == ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY
            else "local dry-run rehearsal completed without executable path"
        )

    expected_state_transition = (
        "REHEARSED_TO_REVIEW_READY"
        if decision == ControlledMockDryRunDecision.MOCK_EXECUTION_REVIEW_READY
        else "REHEARSED_ONLY"
        if decision == ControlledMockDryRunDecision.DRY_RUN_REHEARSED
        else "WATCH_ONLY"
        if decision == ControlledMockDryRunDecision.WATCH_ONLY
        else "BLOCKED"
        if decision == ControlledMockDryRunDecision.BLOCKED
        else "GAP"
    )

    preview = MockOrderIntentPreview(
        intent_id=f"{review_input.dry_run_id}-PREVIEW",
        symbol=review_input.candidate_symbol,
        market=review_input.candidate_market,
        side=review_input.candidate_side,
        candidate_action_type=review_input.candidate_action_type,
        route_type=MockIntentRouteType.WATCH_ONLY if decision in {ControlledMockDryRunDecision.WATCH_ONLY, ControlledMockDryRunDecision.GAP} else MockIntentRouteType.BLOCKED if decision == ControlledMockDryRunDecision.BLOCKED else route_type,
        quantity_preview=review_input.quantity_preview if decision not in {ControlledMockDryRunDecision.BLOCKED, ControlledMockDryRunDecision.WATCH_ONLY} else 0,
        notional_preview=review_input.notional_preview if decision not in {ControlledMockDryRunDecision.BLOCKED, ControlledMockDryRunDecision.WATCH_ONLY} else 0.0,
        stop_discipline_ref=review_input.stop_discipline_ref,
        event_restriction_ref=review_input.event_risk_ref,
        market_regime_constraint_ref=review_input.market_regime_ref,
        breadth_outlier_constraint_ref=review_input.breadth_routing_ref,
        decision_timestamp=review_input.available_at,
        available_at=review_input.available_at,
        no_execution_flag=True,
    )
    summary = ControlledMockDryRunSummaryReport(
        report_id=f"{review_input.dry_run_id}-SUMMARY-REPORT",
        decision=decision,
        decision_reason=reason,
        route_type=preview.route_type,
        expected_state_transition=expected_state_transition,
    )

    preflight = _status_report(
        f"{review_input.dry_run_id}-PREFLIGHT-REPORT",
        "PASS" if decision not in {ControlledMockDryRunDecision.BLOCKED, ControlledMockDryRunDecision.GAP} else "FAIL",
        decision not in {ControlledMockDryRunDecision.BLOCKED, ControlledMockDryRunDecision.GAP},
        warnings,
    )
    provider = _status_report(
        f"{review_input.dry_run_id}-PROVIDER-REPORT",
        review_input.provider_registry_decision or "UNKNOWN",
        review_input.provider_registry_decision not in {"BLOCKED", "GAP", "REJECTED", None},
    )
    market_regime = _status_report(
        f"{review_input.dry_run_id}-MARKET-REGIME-REPORT",
        review_input.market_regime_decision or "UNKNOWN",
        review_input.market_regime_decision not in {"BLOCKED", "GAP", "REJECTED", None},
        [review_input.market_regime_label] if review_input.market_regime_label else [],
    )
    position_sizing = _status_report(
        f"{review_input.dry_run_id}-POSITION-SIZING-REPORT",
        review_input.position_sizing_decision or "UNKNOWN",
        review_input.position_sizing_decision in {"SIZE_READY", "REDUCE_SIZE", "CASH_LIMITED", "RISK_BUDGET_LIMITED"},
    )
    event_risk = _status_report(
        f"{review_input.dry_run_id}-EVENT-RISK-REPORT",
        review_input.event_risk_decision or "UNKNOWN",
        review_input.event_risk_decision not in {"BLOCK_NEW_ENTRY", "BLOCKED", "DATA_GAP", "REJECTED", None},
    )
    breadth = _status_report(
        f"{review_input.dry_run_id}-BREADTH-ROUTING-REPORT",
        review_input.breadth_routing_decision or "UNKNOWN",
        review_input.breadth_routing_decision not in {"WATCH_NON_LEADERS", "BLOCK_CHASING", "BLOCKED", "DATA_GAP", "REJECTED", None},
        review_input.breadth_constraints,
    )
    order_gate = _status_report(
        f"{review_input.dry_run_id}-ORDER-GATE-REPORT",
        "PASS" if _present(review_input.order_gate_boundary_ref) else "FAIL",
        _present(review_input.order_gate_boundary_ref),
    )
    risk_budget = _status_report(
        f"{review_input.dry_run_id}-RISK-BUDGET-REPORT",
        "PASS" if review_input.position_sizing_decision in {"SIZE_READY", "REDUCE_SIZE", "CASH_LIMITED", "RISK_BUDGET_LIMITED"} else "FAIL",
        review_input.position_sizing_decision in {"SIZE_READY", "REDUCE_SIZE", "CASH_LIMITED", "RISK_BUDGET_LIMITED"},
    )
    kill_switch = _status_report(
        f"{review_input.dry_run_id}-KILL-SWITCH-REPORT",
        "PASS" if _present(review_input.kill_switch_policy_ref) else "FAIL",
        _present(review_input.kill_switch_policy_ref),
    )
    rollback = _status_report(
        f"{review_input.dry_run_id}-ROLLBACK-REPORT",
        "PASS" if _present(review_input.rollback_policy_ref) else "FAIL",
        _present(review_input.rollback_policy_ref),
    )
    audit = _status_report(
        f"{review_input.dry_run_id}-AUDIT-REPORT",
        "PASS" if _present(review_input.audit_policy_ref) else "FAIL",
        _present(review_input.audit_policy_ref),
    )

    for gap in gaps:
        if gap.severity == "BLOCKING":
            blocked_findings.append(gap.gap_category)

    boundary = MockBoundaryViolationReport(
        report_id=f"{review_input.dry_run_id}-BOUNDARY-VIOLATION-REPORT",
        real_broker_call_attempt=review_input.real_broker_dependency,
        kiwoom_api_call_attempt=review_input.kiwoom_dependency,
        kiwoom_mock_order_execution_attempt=review_input.kiwoom_mock_order_execution_dependency,
        provider_network_execution_path=review_input.provider_network_dependency,
        production_domain=review_input.live_prod_path_attempt,
        websocket_dependency=review_input.websocket_dependency,
        autonomous_execution_path=review_input.autonomous_execution_path,
        executable_order_object_present=review_input.executable_order_object_present,
        real_order_id_present=review_input.real_order_id_present,
        raw_account_output_present=review_input.raw_account_output_present,
        credential_token_output_present=review_input.credential_token_output_present,
        missing_fail_closed_behavior=review_input.missing_fail_closed_behavior,
        findings=blocked_findings,
    )

    gaps.append(_gap(review_input.dry_run_id, "REPORT-GENERATED", "DRY_RUN_REPORT_GENERATED", "REPORT_ONLY", "controlled mock dry-run report generated"))
    gap_report = ControlledMockDryRunGapReport(
        gap_report_id=f"{review_input.dry_run_id}-GAP-REPORT",
        decision=decision,
        gap_entries=gaps,
        blocking_gap_count=sum(1 for item in gaps if item.severity == "BLOCKING"),
        warning_gap_count=sum(1 for item in gaps if item.severity == "WARNING"),
    )

    return review_input.model_copy(
        update={
            "summary_report": summary,
            "mock_order_intent_preview": preview,
            "preflight_rehearsal_report": preflight,
            "provider_readiness_rehearsal_report": provider,
            "market_regime_rehearsal_report": market_regime,
            "position_sizing_rehearsal_report": position_sizing,
            "event_risk_rehearsal_report": event_risk,
            "breadth_outlier_routing_rehearsal_report": breadth,
            "order_gate_rehearsal_report": order_gate,
            "risk_budget_rehearsal_report": risk_budget,
            "kill_switch_rehearsal_report": kill_switch,
            "rollback_rehearsal_report": rollback,
            "audit_trail_rehearsal_report": audit,
            "boundary_violation_report": boundary,
            "gap_report": gap_report,
        }
    )
