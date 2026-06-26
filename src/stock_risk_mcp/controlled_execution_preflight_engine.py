from __future__ import annotations

from stock_risk_mcp.controlled_execution_adapter import build_controlled_execution_adapter_capability_report
from stock_risk_mcp.controlled_execution_approval_engine import (
    build_controlled_execution_approval_packet,
    validate_controlled_execution_manual_approval,
)
from stock_risk_mcp.controlled_execution_audit_engine import build_controlled_execution_audit_record
from stock_risk_mcp.controlled_execution_duplicate_guard import build_controlled_execution_duplicate_guard_state
from stock_risk_mcp.controlled_execution_guard import validate_controlled_execution_input_gate
from stock_risk_mcp.controlled_execution_killswitch_engine import build_controlled_execution_kill_switch_state
from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionGapEntry,
    ControlledExecutionGapReport,
    ControlledExecutionIntent,
    ControlledExecutionMode,
    ControlledExecutionOrderDraft,
    ControlledExecutionPreflightDecision,
    ControlledExecutionPreflightRequest,
    ControlledExecutionPrerequisiteCheck,
    ControlledExecutionPrerequisiteStatus,
    ControlledExecutionProvider,
    ControlledExecutionReadinessReport,
    ControlledExecutionReadinessStatus,
    ControlledExecutionReconciliationCheckResult,
    ControlledExecutionRiskCheckResult,
    ControlledExecutionSafetyReport,
    ControlledExecutionPipelineInput,
    ControlledExecutionPipelineResult,
)
from stock_risk_mcp.controlled_execution_rehearsal_engine import (
    build_controlled_execution_dry_run_result,
    build_controlled_execution_mock_execution_result,
)


def _status(ok: bool, blocked: bool = False, stale: bool = False, ambiguous: bool = False) -> ControlledExecutionPrerequisiteStatus:
    if ambiguous:
        return ControlledExecutionPrerequisiteStatus.AMBIGUOUS
    if stale:
        return ControlledExecutionPrerequisiteStatus.STALE
    if blocked:
        return ControlledExecutionPrerequisiteStatus.BLOCKED
    return ControlledExecutionPrerequisiteStatus.GREEN if ok else ControlledExecutionPrerequisiteStatus.MISSING


def _check(name: str, status: ControlledExecutionPrerequisiteStatus, *reason_codes: str) -> ControlledExecutionPrerequisiteCheck:
    return ControlledExecutionPrerequisiteCheck(
        prerequisite_name=name,
        prerequisite_status=status,
        reason_codes=[code for code in reason_codes if code],
    )


def _is_green(status: ControlledExecutionPrerequisiteStatus) -> bool:
    return status == ControlledExecutionPrerequisiteStatus.GREEN


def build_controlled_execution_preflight(
    pipeline_input: ControlledExecutionPipelineInput,
    *,
    in_pytest: bool = False,
) -> ControlledExecutionPipelineResult:
    readiness_status, gate_findings, gate_gaps = validate_controlled_execution_input_gate(pipeline_input, in_pytest=in_pytest)

    checks = [
        _check(
            "DATASET_SIGNAL",
            _status(
                bool(pipeline_input.feature_store_manifest)
                and str(pipeline_input.leakage_report.get("readiness_status", "")).upper() != "BLOCKED_LEAKAGE"
                and bool(pipeline_input.paper_evaluation_report)
                and not bool(pipeline_input.paper_evaluation_report.get("signal_used_labels", False))
                and bool(pipeline_input.paper_evaluation_report.get("metrics_available", True)),
                blocked=str(pipeline_input.paper_evaluation_report.get("readiness_status", "")).upper() in {"LEAKAGE_BLOCKED", "REJECTED"},
            ),
            "V10_MANIFEST_REQUIRED" if not pipeline_input.feature_store_manifest else "",
            "LEAKAGE_BLOCKED" if str(pipeline_input.leakage_report.get("readiness_status", "")).upper() == "BLOCKED_LEAKAGE" else "",
        ),
        _check(
            "MACRO_EVENT",
            _status(
                bool(pipeline_input.macro_regime_report) and bool(pipeline_input.event_risk_report),
                blocked=str(pipeline_input.event_risk_report.get("decision", "")).upper() in {"BLOCK_NEW_ENTRY", "BLOCKED", "REJECTED"},
                stale=bool(pipeline_input.macro_regime_report.get("stale", False)) or bool(pipeline_input.event_risk_report.get("stale", False)),
            ),
        ),
        _check(
            "DOMESTIC_SNAPSHOT",
            _status(
                bool(pipeline_input.domestic_snapshot_report)
                and bool(pipeline_input.domestic_snapshot_report.get("liquidity_safe", True)),
                stale=bool(pipeline_input.domestic_snapshot_report.get("stale", False)),
                blocked=not bool(pipeline_input.domestic_snapshot_report.get("liquidity_safe", True)),
            ),
        ),
        _check(
            "RISK",
            _status(
                bool(pipeline_input.position_sizing_report)
                and bool(pipeline_input.risk_budget_ref or pipeline_input.position_sizing_report.get("risk_budget_ref"))
                and not bool(pipeline_input.position_sizing_report.get("unbounded_size", False)),
                blocked=bool(pipeline_input.position_sizing_report.get("unbounded_size", False)),
            ),
        ),
        _check(
            "ACCOUNT_RECONCILIATION",
            _status(
                bool(pipeline_input.account_read_report)
                and bool(pipeline_input.reconciliation_report)
                and bool(pipeline_input.account_read_report.get("account_ref_redacted", True))
                and bool(pipeline_input.reconciliation_report.get("instrument_mapping_unambiguous", True)),
                stale=bool(pipeline_input.account_read_report.get("stale", False)),
                ambiguous=not bool(pipeline_input.reconciliation_report.get("instrument_mapping_unambiguous", True)),
            ),
        ),
        _check(
            "ADAPTER",
            _status(
                bool(pipeline_input.adapter_evidence.get("mock_ready"))
                and bool(pipeline_input.adapter_evidence.get("dry_run_ready")),
            ),
        ),
        _check(
            "APPROVAL",
            _status(True),
        ),
        _check(
            "KILL_SWITCH",
            _status(
                not any(
                    (
                        pipeline_input.global_kill_switch_active,
                        pipeline_input.market_kill_switch_active,
                        pipeline_input.instrument_kill_switch_active,
                        pipeline_input.daily_loss_breached,
                        pipeline_input.max_order_count_breached,
                        pipeline_input.max_exposure_breached,
                        pipeline_input.stale_data_blocked,
                        pipeline_input.cooldown_active,
                    )
                ),
                blocked=any(
                    (
                        pipeline_input.global_kill_switch_active,
                        pipeline_input.market_kill_switch_active,
                        pipeline_input.instrument_kill_switch_active,
                        pipeline_input.daily_loss_breached,
                        pipeline_input.max_order_count_breached,
                        pipeline_input.max_exposure_breached,
                        pipeline_input.cooldown_active,
                    )
                ),
                stale=pipeline_input.stale_data_blocked,
            ),
        ),
        _check(
            "DUPLICATE_GUARD",
            _status(
                not any(
                    (
                        pipeline_input.prior_open_intent_exists,
                        pipeline_input.prior_pending_draft_exists,
                        pipeline_input.same_instrument_side_collision,
                        pipeline_input.prior_pending_audit_unresolved,
                        pipeline_input.approval_reuse_detected,
                    )
                ),
                blocked=any(
                    (
                        pipeline_input.prior_open_intent_exists,
                        pipeline_input.prior_pending_draft_exists,
                        pipeline_input.same_instrument_side_collision,
                        pipeline_input.prior_pending_audit_unresolved,
                        pipeline_input.approval_reuse_detected,
                    )
                ),
            ),
        ),
        _check(
            "CREDENTIAL_NETWORK",
            _status(
                True,
                blocked=pipeline_input.mode == ControlledExecutionMode.LIVE_EXECUTION_OPT_IN_BOUNDARY,
            ),
        ),
    ]

    all_green = not gate_gaps and all(_is_green(check.prerequisite_status) for check in checks)
    reason_codes = gate_findings + [
        check.prerequisite_name
        for check in checks
        if check.prerequisite_status != ControlledExecutionPrerequisiteStatus.GREEN
    ]
    readiness = (
        ControlledExecutionReadinessStatus.PREFLIGHT_READY
        if all_green
        else ControlledExecutionReadinessStatus.BLOCKED
        if reason_codes
        else readiness_status
    )
    readiness_report = ControlledExecutionReadinessReport(
        report_id=f"{pipeline_input.pipeline_id}-READINESS-REPORT",
        pipeline_id=pipeline_input.pipeline_id,
        mode=pipeline_input.mode,
        readiness_status=readiness,
        prerequisite_checks=checks,
        all_green=all_green,
        reason_codes=reason_codes or ["BLOCKED_DEFAULT"],
    )
    preflight_request = ControlledExecutionPreflightRequest(
        request_id=f"{pipeline_input.pipeline_id}-PREFLIGHT-REQUEST",
        pipeline_id=pipeline_input.pipeline_id,
        mode=pipeline_input.mode,
        requested_at=pipeline_input.requested_at,
        requested_by=pipeline_input.requested_by,
    )
    preflight_decision = ControlledExecutionPreflightDecision(
        decision_id=f"{pipeline_input.pipeline_id}-PREFLIGHT-DECISION",
        pipeline_id=pipeline_input.pipeline_id,
        mode=pipeline_input.mode,
        readiness_status=readiness,
        all_green=all_green,
        approved_for_draft=all_green,
        approved_for_live_boundary=False,
        reason_codes=reason_codes or ["BLOCKED_DEFAULT"],
    )
    risk_check_result = ControlledExecutionRiskCheckResult(
        check_id=f"{pipeline_input.pipeline_id}-RISK-CHECK",
        risk_budget_ref=pipeline_input.risk_budget_ref or str(pipeline_input.position_sizing_report.get("risk_budget_ref", "RISK-BUDGET-REF")),
        prerequisite_status=next(check.prerequisite_status for check in checks if check.prerequisite_name == "RISK"),
        bounded_position_size=not bool(pipeline_input.position_sizing_report.get("unbounded_size", False)),
        daily_order_cap_checked=True,
        price_band_checked=True,
        reason_codes=["RISK_OK" if all_green else "RISK_BLOCKED"],
    )
    reconciliation_check_result = ControlledExecutionReconciliationCheckResult(
        check_id=f"{pipeline_input.pipeline_id}-RECONCILIATION-CHECK",
        prerequisite_status=next(check.prerequisite_status for check in checks if check.prerequisite_name == "ACCOUNT_RECONCILIATION"),
        account_ref_redacted=bool(pipeline_input.account_read_report.get("account_ref_redacted", True)),
        account_read_only=bool(pipeline_input.account_read_report.get("read_only", True)),
        instrument_mapping_unambiguous=bool(pipeline_input.reconciliation_report.get("instrument_mapping_unambiguous", True)),
        cash_position_mismatch_classified=bool(pipeline_input.reconciliation_report.get("cash_position_mismatch_classified", True)),
        reason_codes=["RECONCILIATION_OK" if all_green else "RECONCILIATION_BLOCKED"],
    )
    execution_intent = ControlledExecutionIntent(
        intent_id=f"{pipeline_input.pipeline_id}-INTENT",
        instrument_id=pipeline_input.instrument_id,
        provider_symbol=pipeline_input.provider_symbol,
        market=pipeline_input.market,
        side=pipeline_input.side,
        reference_price=pipeline_input.reference_price,
        quantity_proposal=pipeline_input.quantity_proposal if all_green else 0.0,
        notional_proposal=pipeline_input.notional_proposal if all_green else 0.0,
        risk_budget_ref=pipeline_input.risk_budget_ref or "RISK-BUDGET-REF",
        source_report_refs=["v10-manifest", "v11-paper-evaluation", "v12-reconciliation"],
        reason_codes=reason_codes or ["BLOCKED_DEFAULT"],
        preflight_status=readiness,
    )
    draft_hash = f"DRAFT-{pipeline_input.pipeline_id}-{pipeline_input.instrument_id}-{pipeline_input.side.value}"
    order_draft = ControlledExecutionOrderDraft(
        draft_id=f"{pipeline_input.pipeline_id}-ORDER-DRAFT",
        instrument_id=pipeline_input.instrument_id,
        side=pipeline_input.side,
        quantity=pipeline_input.quantity_proposal if all_green else 0.0,
        order_type="LIMIT",
        limit_price=pipeline_input.reference_price,
        time_in_force="DAY",
        idempotency_key=pipeline_input.idempotency_key,
        draft_hash=draft_hash,
        risk_checks=[risk_check_result.check_id],
        reconciliation_checks=[reconciliation_check_result.check_id],
        adapter_target=pipeline_input.provider,
        status=readiness,
        live_submit_preview_blocked=True,
    )
    kill_switch_state = build_controlled_execution_kill_switch_state(pipeline_input)
    duplicate_guard_state = build_controlled_execution_duplicate_guard_state(pipeline_input)
    adapter_capability_report = build_controlled_execution_adapter_capability_report(pipeline_input)
    approval_packet = build_controlled_execution_approval_packet(
        pipeline_input,
        order_draft,
        kill_switch_summary={"clear_for_preflight": kill_switch_state.clear_for_preflight},
        duplicate_summary={"clear_for_preflight": duplicate_guard_state.clear_for_preflight},
        risk_summary={"bounded_position_size": risk_check_result.bounded_position_size},
        reconciliation_summary={"instrument_mapping_unambiguous": reconciliation_check_result.instrument_mapping_unambiguous},
        adapter_summary={"provider": pipeline_input.provider.value},
    )
    manual_approval = validate_controlled_execution_manual_approval(pipeline_input, order_draft, approval_packet)
    mock_execution_result = build_controlled_execution_mock_execution_result(
        pipeline_input,
        order_draft,
        approval_valid=manual_approval.valid and all_green and kill_switch_state.clear_for_preflight and duplicate_guard_state.clear_for_preflight,
    )
    schema_evidence_present = any(row.exact_schema_evidence_present for row in adapter_capability_report.adapter_rows if row.provider == pipeline_input.provider)
    dry_run_result = build_controlled_execution_dry_run_result(
        pipeline_input,
        order_draft,
        schema_evidence_present=schema_evidence_present or pipeline_input.provider in {ControlledExecutionProvider.LOCAL_MOCK, ControlledExecutionProvider.DRY_RUN},
    )
    audit_records = [
        build_controlled_execution_audit_record(
            pipeline_id=pipeline_input.pipeline_id,
            action_type="PREFLIGHT",
            created_at=pipeline_input.requested_at,
            mode=pipeline_input.mode,
            decision=preflight_decision.readiness_status.value,
            source_refs=execution_intent.source_report_refs,
            order_draft_hash=order_draft.draft_hash,
            idempotency_key=pipeline_input.idempotency_key,
            reason_codes=preflight_decision.reason_codes,
        ),
        build_controlled_execution_audit_record(
            pipeline_id=pipeline_input.pipeline_id,
            action_type="APPROVAL",
            created_at=pipeline_input.requested_at,
            mode=pipeline_input.mode,
            decision="APPROVAL_VALID" if manual_approval.valid else "APPROVAL_INVALID",
            source_refs=execution_intent.source_report_refs,
            order_draft_hash=order_draft.draft_hash,
            approval_ref_hash=manual_approval.approval_ref_hash,
            idempotency_key=pipeline_input.idempotency_key,
            reason_codes=manual_approval.reason_codes,
        ),
        build_controlled_execution_audit_record(
            pipeline_id=pipeline_input.pipeline_id,
            action_type="MOCK_EXECUTION",
            created_at=pipeline_input.requested_at,
            mode=pipeline_input.mode,
            decision=mock_execution_result.simulated_status,
            source_refs=execution_intent.source_report_refs,
            order_draft_hash=order_draft.draft_hash,
            approval_ref_hash=manual_approval.approval_ref_hash,
            idempotency_key=pipeline_input.idempotency_key,
            reason_codes=mock_execution_result.reason_codes,
        ),
        build_controlled_execution_audit_record(
            pipeline_id=pipeline_input.pipeline_id,
            action_type="DRY_RUN",
            created_at=pipeline_input.requested_at,
            mode=pipeline_input.mode,
            decision=dry_run_result.preview_status,
            source_refs=execution_intent.source_report_refs,
            order_draft_hash=order_draft.draft_hash,
            approval_ref_hash=manual_approval.approval_ref_hash,
            idempotency_key=pipeline_input.idempotency_key,
            reason_codes=dry_run_result.reason_codes,
        ),
    ]
    gap_entries = gate_gaps + [
        ControlledExecutionGapEntry(
            gap_id=f"{pipeline_input.pipeline_id}-{code}",
            gap_category="PREREQUISITE_BLOCKED",
            severity="BLOCKING",
            message=f"{code} blocks controlled execution",
        )
        for code in reason_codes
        if code not in gate_findings
    ]
    safety_report = ControlledExecutionSafetyReport(
        report_id=f"{pipeline_input.pipeline_id}-SAFETY-REPORT",
        pipeline_id=pipeline_input.pipeline_id,
        findings=[
            "READ_ONLY",
            "REPORT_ONLY",
            "NO_NETWORK",
            "NO_ACCOUNT_MUTATION",
            "NO_EXECUTABLE_OUTPUT",
        ],
    )
    gap_report = ControlledExecutionGapReport(
        report_id=f"{pipeline_input.pipeline_id}-GAP-REPORT",
        pipeline_id=pipeline_input.pipeline_id,
        readiness_status=readiness,
        gap_entries=gap_entries,
    )
    return ControlledExecutionPipelineResult(
        readiness_report=readiness_report,
        preflight_request=preflight_request,
        preflight_decision=preflight_decision,
        risk_check_result=risk_check_result,
        reconciliation_check_result=reconciliation_check_result,
        execution_intent=execution_intent,
        order_draft=order_draft,
        approval_packet=approval_packet,
        manual_approval=manual_approval,
        kill_switch_state=kill_switch_state,
        duplicate_guard_state=duplicate_guard_state,
        adapter_capability_report=adapter_capability_report,
        mock_execution_result=mock_execution_result,
        dry_run_result=dry_run_result,
        audit_records=audit_records,
        safety_report=safety_report,
        gap_report=gap_report,
    )
