from __future__ import annotations

from datetime import datetime, timezone

from stock_risk_mcp.kiwoom_mock_api_preflight_gate_models import (
    KiwoomMockApiExecutionReadiness,
    KiwoomMockApiPreflightAuditRecord,
    KiwoomMockApiPreflightGateConfig,
    KiwoomMockApiPreflightGapCategory,
    KiwoomMockApiPreflightGapReport,
    KiwoomMockApiPreflightReadinessReport,
    KiwoomMockApiPreflightRequestCategory,
    KiwoomMockApiPreflightSafetyReport,
)


_BLOCKED_CAPABILITIES = [
    "OAUTH_EXECUTION_BLOCKED",
    "ACCOUNT_ENDPOINT_BLOCKED",
    "ORDER_ENDPOINT_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
    "TOKEN_LOADING_BLOCKED",
    "TOKEN_USAGE_BLOCKED",
    "TOKEN_REFRESH_BLOCKED",
    "HTTP_CLIENT_CREATION_BLOCKED",
    "HTTP_SESSION_CREATION_BLOCKED",
    "TRANSPORT_CREATION_BLOCKED",
    "API_CALL_BLOCKED",
    "MOCKAPI_CALL_BLOCKED",
    "NETWORK_EXECUTION_BLOCKED",
    "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
]


def _classify(config: KiwoomMockApiPreflightGateConfig) -> tuple[KiwoomMockApiPreflightRequestCategory, KiwoomMockApiExecutionReadiness, str]:
    endpoint = config.transport_draft_config.endpoint_evidence_ref
    category = endpoint.documented_category.strip().upper()
    path = endpoint.documented_path.strip()

    if path in {"/oauth2/token", "/oauth2/revoke"}:
        return (
            KiwoomMockApiPreflightRequestCategory.OAUTH,
            KiwoomMockApiExecutionReadiness.BLOCKED,
            "oauth endpoints remain blocked from execution",
        )
    if category == "ACCOUNT" or path.startswith("/api/dostk/acnt"):
        return (
            KiwoomMockApiPreflightRequestCategory.ACCOUNT,
            KiwoomMockApiExecutionReadiness.BLOCKED,
            "account endpoints remain blocked from execution",
        )
    if category == "ORDER" or "/ordr" in path:
        return (
            KiwoomMockApiPreflightRequestCategory.ORDER,
            KiwoomMockApiExecutionReadiness.BLOCKED,
            "order endpoints remain blocked from execution",
        )
    if category == "WEBSOCKET" or "websocket" in path:
        return (
            KiwoomMockApiPreflightRequestCategory.WEBSOCKET,
            KiwoomMockApiExecutionReadiness.BLOCKED,
            "websocket endpoints remain blocked from execution",
        )
    if category == "QUOTE" and endpoint.documented_mock_domain == "https://mockapi.kiwoom.com":
        if path == "/api/dostk/mrkcond":
            return (
                KiwoomMockApiPreflightRequestCategory.QUOTE,
                KiwoomMockApiExecutionReadiness.DRAFT_READY,
                "mock-domain quote draft is a future execution candidate only",
            )
        return (
            KiwoomMockApiPreflightRequestCategory.QUOTE,
            KiwoomMockApiExecutionReadiness.GAP,
            "quote draft remains non-executable until future execution prerequisites are implemented",
        )
    return (
        KiwoomMockApiPreflightRequestCategory.UNKNOWN,
        KiwoomMockApiExecutionReadiness.REJECTED,
        "unknown endpoint drafts remain rejected",
    )


def run_kiwoom_mock_api_preflight_gate(
    config: KiwoomMockApiPreflightGateConfig,
) -> KiwoomMockApiPreflightGateConfig:
    request_category, readiness_decision, rationale = _classify(config)

    gap_categories = [
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_EXECUTION_NOT_IMPLEMENTED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_HTTP_CLIENT_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_HTTP_SESSION_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_TRANSPORT_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_TOKEN_LOADING_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_TOKEN_USAGE_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_TOKEN_REFRESH_NOT_ALLOWED,
        KiwoomMockApiPreflightGapCategory.PREFLIGHT_AUTHORIZATION_HEADER_NOT_ALLOWED,
    ]

    if request_category == KiwoomMockApiPreflightRequestCategory.OAUTH:
        gap_categories.append(KiwoomMockApiPreflightGapCategory.PREFLIGHT_OAUTH_ENDPOINT_BLOCKED)
    elif request_category == KiwoomMockApiPreflightRequestCategory.ACCOUNT:
        gap_categories.append(KiwoomMockApiPreflightGapCategory.PREFLIGHT_ACCOUNT_ENDPOINT_BLOCKED)
    elif request_category == KiwoomMockApiPreflightRequestCategory.ORDER:
        gap_categories.append(KiwoomMockApiPreflightGapCategory.PREFLIGHT_ORDER_ENDPOINT_BLOCKED)
    elif request_category == KiwoomMockApiPreflightRequestCategory.WEBSOCKET:
        gap_categories.append(KiwoomMockApiPreflightGapCategory.PREFLIGHT_WEBSOCKET_ENDPOINT_BLOCKED)
    elif request_category == KiwoomMockApiPreflightRequestCategory.UNKNOWN:
        gap_categories.append(KiwoomMockApiPreflightGapCategory.PREFLIGHT_UNKNOWN_ENDPOINT_REJECTED)

    findings = [
        "preflight_gate_evaluated=true",
        "http_client_created=false",
        "http_session_created=false",
        "transport_created=false",
        "network_execution_enabled=false",
        f"request_category={request_category.value}",
        f"readiness_decision={readiness_decision.value}",
    ]

    readiness_report = KiwoomMockApiPreflightReadinessReport(
        readiness_report_id=f"{config.config_id}-READINESS",
        request_category=request_category,
        readiness_decision=readiness_decision,
        rationale=rationale,
        blocked_capabilities=list(_BLOCKED_CAPABILITIES),
    )
    safety_report = KiwoomMockApiPreflightSafetyReport(
        safety_report_id=f"{config.config_id}-SAFETY",
        blocked_capabilities=list(_BLOCKED_CAPABILITIES),
        findings=findings,
    )
    gap_report = KiwoomMockApiPreflightGapReport(
        gap_report_id=f"{config.config_id}-GAP",
        gap_status="UNRESOLVED_IMPLEMENTATION_GAPS",
        gap_categories=gap_categories,
        blocking_gap_count=len(gap_categories),
        report_only_gap_count=0,
        gaps=[category.value for category in gap_categories],
    )
    audit_records = [
        KiwoomMockApiPreflightAuditRecord(
            audit_record_id=f"{config.config_id}-AUDIT",
            created_at=datetime.now(timezone.utc),
            source_path="fixtures/kiwoom/kiwoom_mock_api_preflight_gate_fixture.json",
            redaction_applied=True,
            contains_secret_material=False,
            evidence_refs=[
                "KIWOOM-REST-EVIDENCE-PACK",
                "KIWOOM-CAPABILITY-MATRIX",
                "V6.4-CREDENTIAL-BOUNDARY",
                "V6.5-OAUTH-DRAFT-BOUNDARY",
                "V6.6-TRANSPORT-DRAFT-BOUNDARY",
            ],
        )
    ]

    return config.model_copy(
        update={
            "readiness_report": readiness_report,
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )
