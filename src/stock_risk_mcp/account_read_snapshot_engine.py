from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.account_read_adapter import (
    build_account_read_execution_decision,
    build_account_read_provider_capability_report,
    build_account_read_request_preview,
    parse_account_read_snapshot,
)
from stock_risk_mcp.account_read_guard import validate_account_read_input_gate
from stock_risk_mcp.account_read_models import (
    AccountReadCompletenessReport,
    AccountReadFreshnessReport,
    AccountReadGapReport,
    AccountReadPipelineInput,
    AccountReadPipelineResult,
    AccountReadReadinessStatus,
    AccountReadSafetyReport,
    AccountReadSnapshot,
)


def _minutes_between(lhs: datetime, rhs: datetime) -> int:
    return max(int((lhs - rhs).total_seconds() // 60), 0)


def _build_freshness_report(snapshot: AccountReadSnapshot, *, requested_at: datetime) -> AccountReadFreshnessReport:
    age_minutes = _minutes_between(requested_at, snapshot.metadata.available_at)
    stale = age_minutes > 1440
    return AccountReadFreshnessReport(
        report_id=f"{snapshot.metadata.snapshot_id}-FRESHNESS-REPORT",
        snapshot_id=snapshot.metadata.snapshot_id,
        readiness_status=AccountReadReadinessStatus.STALE if stale else AccountReadReadinessStatus.ACCOUNT_READ_SNAPSHOT_READY,
        stale_threshold_minutes=1440,
        age_minutes=age_minutes,
        stale=stale,
    )


def _build_completeness_report(snapshot: AccountReadSnapshot) -> AccountReadCompletenessReport:
    holdings_present = bool(snapshot.holdings)
    cash_present = bool(snapshot.cash_balances)
    covered = [holding for holding in snapshot.holdings if holding.average_cost is not None]
    average_cost_coverage = len(covered) / len(snapshot.holdings) if snapshot.holdings else 0.0
    missing_fields: list[str] = []
    if not holdings_present:
        missing_fields.append("HOLDINGS")
    if not cash_present:
        missing_fields.append("CASH_BALANCES")
    if average_cost_coverage < 1.0:
        missing_fields.append("AVERAGE_COST")
    if snapshot.total_market_value is None:
        missing_fields.append("TOTAL_MARKET_VALUE")
    readiness = AccountReadReadinessStatus.ACCOUNT_READ_SNAPSHOT_READY if not missing_fields else AccountReadReadinessStatus.ACCOUNT_READ_INCOMPLETE
    return AccountReadCompletenessReport(
        report_id=f"{snapshot.metadata.snapshot_id}-COMPLETENESS-REPORT",
        snapshot_id=snapshot.metadata.snapshot_id,
        readiness_status=readiness,
        holdings_present=holdings_present,
        cash_present=cash_present,
        average_cost_coverage=average_cost_coverage,
        total_market_value_present=snapshot.total_market_value is not None,
        missing_fields=missing_fields,
    )


def build_account_read_snapshot_pipeline(
    pipeline_input: AccountReadPipelineInput,
    *,
    in_pytest: bool = False,
) -> AccountReadPipelineResult:
    readiness, findings, gaps = validate_account_read_input_gate(pipeline_input, in_pytest=in_pytest)
    capability_report = build_account_read_provider_capability_report()
    request_preview = build_account_read_request_preview(pipeline_input)
    execution_decision = build_account_read_execution_decision(pipeline_input, readiness, findings)
    snapshot = parse_account_read_snapshot(pipeline_input.snapshot_fixture) if pipeline_input.snapshot_fixture else None
    freshness_report = _build_freshness_report(snapshot, requested_at=pipeline_input.requested_at) if snapshot else None
    completeness_report = _build_completeness_report(snapshot) if snapshot else None
    if snapshot and freshness_report and freshness_report.stale:
        readiness = AccountReadReadinessStatus.STALE
        findings.append("STALE")
    if snapshot and completeness_report and completeness_report.readiness_status == AccountReadReadinessStatus.ACCOUNT_READ_INCOMPLETE:
        findings.append("INCOMPLETE")
    safety_report = AccountReadSafetyReport(
        report_id=f"{pipeline_input.pipeline_id}-SAFETY-REPORT",
        snapshot_id=snapshot.metadata.snapshot_id if snapshot else None,
        findings=findings or ["READ_ONLY_REPORT_ONLY"],
    )
    gap_report = AccountReadGapReport(
        report_id=f"{pipeline_input.pipeline_id}-GAP-REPORT",
        snapshot_id=snapshot.metadata.snapshot_id if snapshot else None,
        readiness_status=readiness,
        gap_entries=gaps,
    )
    return AccountReadPipelineResult(
        capability_report=capability_report,
        request_preview=request_preview,
        execution_decision=execution_decision,
        snapshot=snapshot,
        freshness_report=freshness_report,
        completeness_report=completeness_report,
        safety_report=safety_report,
        gap_report=gap_report,
    )
