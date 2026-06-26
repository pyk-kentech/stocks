from __future__ import annotations

from stock_risk_mcp.portfolio_reconciliation_models import (
    PortfolioComparisonBasis,
    PortfolioMismatchEntry,
    PortfolioMismatchReport,
    PortfolioMismatchStatus,
    PortfolioReconciliationGapEntry,
    PortfolioReconciliationGapReport,
    PortfolioReconciliationIntegrationReport,
    PortfolioReconciliationPipelineInput,
    PortfolioReconciliationPipelineResult,
    PortfolioReconciliationPlanReport,
    PortfolioReconciliationReadinessReport,
    PortfolioReconciliationReadinessStatus,
    PortfolioReconciliationReport,
    PortfolioReconciliationSafetyReport,
    V13ReadinessTier,
)


def _paper_position_map(pipeline_input: PortfolioReconciliationPipelineInput) -> dict[str, object]:
    return {
        position.instrument_id: position
        for position in pipeline_input.paper_evaluation.positions
        if not position.closed
    }


def _account_position_map(pipeline_input: PortfolioReconciliationPipelineInput) -> dict[str, object]:
    return {holding.instrument_id: holding for holding in pipeline_input.account_snapshot.holdings}


def _target_position_map(pipeline_input: PortfolioReconciliationPipelineInput) -> dict[str, object]:
    return {position.instrument_id: position for position in pipeline_input.target_positions}


def _compare_paper_vs_account(
    pipeline_input: PortfolioReconciliationPipelineInput,
) -> list[PortfolioMismatchEntry]:
    paper_positions = _paper_position_map(pipeline_input)
    account_positions = _account_position_map(pipeline_input)
    entries: list[PortfolioMismatchEntry] = []
    for instrument_id in sorted(set(paper_positions) | set(account_positions)):
        paper = paper_positions.get(instrument_id)
        account = account_positions.get(instrument_id)
        if paper is None:
            entries.append(
                PortfolioMismatchEntry(
                    mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-ACCOUNT-ONLY",
                    comparison_basis=PortfolioComparisonBasis.PAPER_VS_ACCOUNT,
                    instrument_id=instrument_id,
                    mismatch_status=PortfolioMismatchStatus.ACCOUNT_ONLY,
                    account_quantity=account.quantity,
                    account_average_cost=account.average_cost,
                    notes=["present in account only"],
                )
            )
            continue
        if account is None:
            entries.append(
                PortfolioMismatchEntry(
                    mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-PAPER-ONLY",
                    comparison_basis=PortfolioComparisonBasis.PAPER_VS_ACCOUNT,
                    instrument_id=instrument_id,
                    mismatch_status=PortfolioMismatchStatus.PAPER_ONLY,
                    paper_quantity=paper.open_quantity,
                    paper_average_cost=paper.average_entry_price,
                    notes=["present in paper only"],
                )
            )
            continue
        quantity_delta = account.quantity - paper.open_quantity
        average_cost_delta = None
        notes: list[str] = []
        if account.average_cost is None:
            notes.append("average cost missing in account snapshot")
        else:
            average_cost_delta = account.average_cost - paper.average_entry_price
        mismatch_status = PortfolioMismatchStatus.MATCH
        if abs(quantity_delta) > 1e-9:
            mismatch_status = PortfolioMismatchStatus.QUANTITY_MISMATCH
        elif average_cost_delta is not None and abs(average_cost_delta) > 1e-9:
            mismatch_status = PortfolioMismatchStatus.PRICE_MISMATCH
        entries.append(
            PortfolioMismatchEntry(
                mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-PAPER-ACCOUNT",
                comparison_basis=PortfolioComparisonBasis.PAPER_VS_ACCOUNT,
                instrument_id=instrument_id,
                mismatch_status=mismatch_status,
                paper_quantity=paper.open_quantity,
                account_quantity=account.quantity,
                quantity_delta=quantity_delta,
                paper_average_cost=paper.average_entry_price,
                account_average_cost=account.average_cost,
                average_cost_delta=average_cost_delta,
                notes=notes,
            )
        )
    return entries


def _compare_target_vs_account(
    pipeline_input: PortfolioReconciliationPipelineInput,
) -> list[PortfolioMismatchEntry]:
    target_positions = _target_position_map(pipeline_input)
    if not target_positions:
        return []
    account_positions = _account_position_map(pipeline_input)
    entries: list[PortfolioMismatchEntry] = []
    for instrument_id in sorted(set(target_positions) | set(account_positions)):
        target = target_positions.get(instrument_id)
        account = account_positions.get(instrument_id)
        if target is None:
            entries.append(
                PortfolioMismatchEntry(
                    mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-ACCOUNT-ONLY-TARGET",
                    comparison_basis=PortfolioComparisonBasis.TARGET_VS_ACCOUNT,
                    instrument_id=instrument_id,
                    mismatch_status=PortfolioMismatchStatus.ACCOUNT_ONLY,
                    account_quantity=account.quantity,
                    account_average_cost=account.average_cost,
                    notes=["target missing"],
                )
            )
            continue
        if account is None:
            entries.append(
                PortfolioMismatchEntry(
                    mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-TARGET-ONLY",
                    comparison_basis=PortfolioComparisonBasis.TARGET_VS_ACCOUNT,
                    instrument_id=instrument_id,
                    mismatch_status=PortfolioMismatchStatus.TARGET_ONLY,
                    target_quantity=target.quantity,
                    notes=["account missing"],
                )
            )
            continue
        quantity_delta = account.quantity - target.quantity
        mismatch_status = PortfolioMismatchStatus.MATCH if abs(quantity_delta) <= 1e-9 else PortfolioMismatchStatus.QUANTITY_MISMATCH
        entries.append(
            PortfolioMismatchEntry(
                mismatch_id=f"{pipeline_input.dataset_id}-{instrument_id}-TARGET-ACCOUNT",
                comparison_basis=PortfolioComparisonBasis.TARGET_VS_ACCOUNT,
                instrument_id=instrument_id,
                mismatch_status=mismatch_status,
                account_quantity=account.quantity,
                target_quantity=target.quantity,
                quantity_delta=quantity_delta,
            )
        )
    return entries


def build_portfolio_reconciliation(
    pipeline_input: PortfolioReconciliationPipelineInput,
) -> PortfolioReconciliationPipelineResult:
    paper_entries = _compare_paper_vs_account(pipeline_input)
    target_entries = _compare_target_vs_account(pipeline_input)
    mismatches = paper_entries + target_entries
    paper_match_count = sum(1 for entry in paper_entries if entry.mismatch_status == PortfolioMismatchStatus.MATCH)
    paper_mismatch_count = len(paper_entries) - paper_match_count
    target_match_count = sum(1 for entry in target_entries if entry.mismatch_status == PortfolioMismatchStatus.MATCH)
    target_mismatch_count = len(target_entries) - target_match_count

    findings: list[str] = []
    gaps: list[PortfolioReconciliationGapEntry] = []
    if not pipeline_input.paper_evaluation.positions:
        findings.append("PAPER_DATA_GAP")
        gaps.append(
            PortfolioReconciliationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-PAPER-DATA-GAP",
                gap_category="PAPER_DATA_GAP",
                severity="BLOCKING",
                message="paper evaluation positions are required",
            )
        )
    if not pipeline_input.account_snapshot.holdings:
        findings.append("ACCOUNT_DATA_GAP")
        gaps.append(
            PortfolioReconciliationGapEntry(
                gap_id=f"{pipeline_input.dataset_id}-ACCOUNT-DATA-GAP",
                gap_category="ACCOUNT_DATA_GAP",
                severity="BLOCKING",
                message="account snapshot holdings are required",
            )
        )
    if any(entry.account_average_cost is None for entry in paper_entries if entry.account_quantity is not None and entry.paper_quantity is not None):
        findings.append("DATA_GAP")

    readiness = PortfolioReconciliationReadinessStatus.RECONCILIATION_REPORT_READY if not gaps else PortfolioReconciliationReadinessStatus.DATA_GAP
    v13_tier = V13ReadinessTier.READY_FOR_MANUAL_REVIEW if not gaps else V13ReadinessTier.PARTIAL
    plan_report = PortfolioReconciliationPlanReport(
        report_id=f"{pipeline_input.pipeline_id}-PLAN-REPORT",
        dataset_id=pipeline_input.dataset_id,
        account_snapshot_id=pipeline_input.account_snapshot.metadata.snapshot_id,
        readiness_status=readiness,
        comparison_bases=[PortfolioComparisonBasis.PAPER_VS_ACCOUNT] + ([PortfolioComparisonBasis.TARGET_VS_ACCOUNT] if pipeline_input.target_positions else []),
        target_positions_supplied=bool(pipeline_input.target_positions),
        v13_readiness_tier=v13_tier,
    )
    reconciliation_report = PortfolioReconciliationReport(
        report_id=f"{pipeline_input.pipeline_id}-RECONCILIATION-REPORT",
        dataset_id=pipeline_input.dataset_id,
        account_snapshot_id=pipeline_input.account_snapshot.metadata.snapshot_id,
        readiness_status=readiness,
        paper_vs_account_match_count=paper_match_count,
        paper_vs_account_mismatch_count=paper_mismatch_count,
        target_vs_account_match_count=target_match_count,
        target_vs_account_mismatch_count=target_mismatch_count,
        mismatch_entries=mismatches,
        comparison_notes=findings,
    )
    mismatch_report = PortfolioMismatchReport(
        report_id=f"{pipeline_input.pipeline_id}-MISMATCH-REPORT",
        dataset_id=pipeline_input.dataset_id,
        mismatch_entries=mismatches,
    )
    readiness_report = PortfolioReconciliationReadinessReport(
        report_id=f"{pipeline_input.pipeline_id}-READINESS-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        v13_readiness_tier=v13_tier,
        findings=findings or ["READ_ONLY_REPORT_ONLY"],
    )
    integration_report = PortfolioReconciliationIntegrationReport(
        report_id=f"{pipeline_input.pipeline_id}-INTEGRATION-REPORT",
        dataset_id=pipeline_input.dataset_id,
        paper_portfolio_ready=bool(pipeline_input.paper_evaluation.positions),
        paper_trade_ready=bool(pipeline_input.paper_evaluation.trades),
        account_snapshot_ready=bool(pipeline_input.account_snapshot.holdings),
        target_positions_ready=bool(pipeline_input.target_positions),
        average_cost_comparison_ready=all(holding.average_cost is not None for holding in pipeline_input.account_snapshot.holdings),
        provider_gap_propagated=bool(gaps),
    )
    safety_report = PortfolioReconciliationSafetyReport(
        report_id=f"{pipeline_input.pipeline_id}-SAFETY-REPORT",
        dataset_id=pipeline_input.dataset_id,
        findings=["READ_ONLY", "REPORT_ONLY", "NO_ORDER", "NO_ACCOUNT_MUTATION"],
    )
    gap_report = PortfolioReconciliationGapReport(
        report_id=f"{pipeline_input.pipeline_id}-GAP-REPORT",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=readiness,
        gap_entries=gaps,
    )
    return PortfolioReconciliationPipelineResult(
        plan_report=plan_report,
        reconciliation_report=reconciliation_report,
        mismatch_report=mismatch_report,
        readiness_report=readiness_report,
        integration_report=integration_report,
        safety_report=safety_report,
        gap_report=gap_report,
    )
