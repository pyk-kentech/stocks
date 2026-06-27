from __future__ import annotations

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureDecision,
    HistoricalChartCaptureRunAudit,
    HistoricalChartCaptureRunResult,
    HistoricalChartCaptureRunTaskResult,
    HistoricalMarketDataCredentialPolicy,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataRedactionStatus,
    HistoricalMarketDataTransportKind,
)


def build_blocked_capture_run_result(
    dataset_id: str,
    *,
    blocked_reasons: list[str],
    transport_kind: HistoricalMarketDataTransportKind,
    credential_ref_present: bool,
) -> HistoricalChartCaptureRunResult:
    return build_capture_run_result_with_status(
        dataset_id,
        readiness_status=HistoricalMarketDataReadinessStatus.BLOCKED,
        blocked_reasons=blocked_reasons,
        transport_kind=transport_kind,
        credential_ref_present=credential_ref_present,
    )


def build_capture_run_result_with_status(
    dataset_id: str,
    *,
    readiness_status: HistoricalMarketDataReadinessStatus,
    blocked_reasons: list[str],
    transport_kind: HistoricalMarketDataTransportKind,
    credential_ref_present: bool,
    task_results: list[HistoricalChartCaptureRunTaskResult] | None = None,
) -> HistoricalChartCaptureRunResult:
    normalized_task_results = task_results or [
        HistoricalChartCaptureRunTaskResult(
            task_id=f"{dataset_id}-BLOCKED",
            request_id=f"{dataset_id}-BLOCKED",
            execution_decision=HistoricalChartCaptureDecision.BLOCKED,
            blocked_reasons=blocked_reasons,
        )
    ]
    audit = HistoricalChartCaptureRunAudit(
        audit_id=f"{dataset_id}-REAL-CAPTURE-AUDIT",
        dataset_id=dataset_id,
        transport_kind=transport_kind,
        credential_ref_present=credential_ref_present,
        credential_policy=HistoricalMarketDataCredentialPolicy.KEY_REF_ONLY if credential_ref_present else HistoricalMarketDataCredentialPolicy.BLOCKED,
        redaction_status=HistoricalMarketDataRedactionStatus.PASSED,
        auth_header_present=credential_ref_present,
        task_results=normalized_task_results,
        blocked_reasons=blocked_reasons,
    )
    return HistoricalChartCaptureRunResult(
        run_id=f"{dataset_id}-REAL-CAPTURE-RUN",
        dataset_id=dataset_id,
        readiness_status=readiness_status,
        task_results=normalized_task_results,
        audit_report=audit,
    )
