from __future__ import annotations

from stock_risk_mcp.historical_market_data_models import (
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
    audit = HistoricalChartCaptureRunAudit(
        audit_id=f"{dataset_id}-REAL-CAPTURE-AUDIT",
        dataset_id=dataset_id,
        transport_kind=transport_kind,
        credential_ref_present=credential_ref_present,
        credential_policy=HistoricalMarketDataCredentialPolicy.KEY_REF_ONLY if credential_ref_present else HistoricalMarketDataCredentialPolicy.BLOCKED,
        redaction_status=HistoricalMarketDataRedactionStatus.PASSED,
        auth_header_present=credential_ref_present,
        blocked_reasons=blocked_reasons,
    )
    return HistoricalChartCaptureRunResult(
        run_id=f"{dataset_id}-REAL-CAPTURE-RUN",
        dataset_id=dataset_id,
        readiness_status=HistoricalMarketDataReadinessStatus.BLOCKED,
        task_results=[
            HistoricalChartCaptureRunTaskResult(
                task_id=f"{dataset_id}-BLOCKED",
                request_id=f"{dataset_id}-BLOCKED",
                execution_decision="BLOCKED",
                blocked_reasons=blocked_reasons,
            )
        ],
        audit_report=audit,
    )
