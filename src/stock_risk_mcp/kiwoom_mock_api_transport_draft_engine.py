from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from stock_risk_mcp.kiwoom_mock_api_transport_draft_guard import (
    validate_kiwoom_mock_api_transport_draft_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiTransportAuditRecord,
    KiwoomMockApiTransportDraftConfig,
    KiwoomMockApiTransportGapCategory,
    KiwoomMockApiTransportGapReport,
    KiwoomMockApiTransportSafetyReport,
)


_BLOCKED_CAPABILITIES = [
    "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
    "TOKEN_LOADING_BLOCKED",
    "TOKEN_USAGE_BLOCKED",
    "TOKEN_REFRESH_BLOCKED",
    "HTTP_CLIENT_CREATION_BLOCKED",
    "HTTP_SESSION_CREATION_BLOCKED",
    "TRANSPORT_CREATION_BLOCKED",
    "API_CALL_BLOCKED",
    "MOCKAPI_CALL_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "NETWORK_EXECUTION_BLOCKED",
    "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
    "LIVE_PROD_BLOCKED",
    "REAL_ACCOUNT_READ_BLOCKED",
    "REAL_ACCOUNT_MUTATION_BLOCKED",
    "REAL_ORDER_BLOCKED",
    "CREDENTIAL_LOADING_BLOCKED",
    "CREDENTIAL_FILE_READ_BLOCKED",
    "ENVIRONMENT_READ_BLOCKED",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_domains() -> dict[str, object]:
    matrix_path = _repo_root() / "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    return dict(matrix.get("domains", {}))


def _validate_local_reference_path(path: str, field_name: str) -> str:
    cleaned = str(path).strip()
    lowered = cleaned.lower()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be local-only")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def run_kiwoom_mock_api_transport_draft_boundary(
    config: KiwoomMockApiTransportDraftConfig,
    *,
    oauth_draft_boundary_ref: str | None = None,
) -> KiwoomMockApiTransportDraftConfig:
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]] = []
    findings: list[str] = []
    domains = _load_domains()

    _validate_endpoint_evidence_ref(config, domains, gap_entries)
    _validate_request_envelope(config, gap_entries)
    _validate_transport_policy(config, domains, gap_entries)
    _validate_retry_timeout_policy(config, gap_entries)
    _validate_error_response_draft(config, gap_entries)
    _validate_oauth_boundary_ref(oauth_draft_boundary_ref, gap_entries, findings)

    findings.extend(
        [
            "draft_bundle_built=true",
            "endpoint_evidence_mode=DOCUMENTATION_ONLY",
            "http_method_mode=REFERENCE_ONLY",
            "authorization_header_generation=false",
            "token_loading=false",
            "token_usage=false",
            "token_refresh=false",
            "http_client_created=false",
            "http_session_created=false",
            "transport_created=false",
            "network_execution_enabled=false",
            "mock_domain_only=true",
        ]
    )

    safety_report = _build_safety_report(config.safety_report, findings, gap_entries)
    gap_report = _build_gap_report(config.gap_report, gap_entries)
    audit_records = _build_audit_records(config.audit_records, config.config_id, oauth_draft_boundary_ref)

    return config.model_copy(
        update={
            "request_envelope_draft": config.request_envelope_draft.model_copy(
                update={
                    "authorization_header_generation_available": False,
                    "http_client_available": False,
                    "http_session_available": False,
                    "network_execution_enabled": False,
                }
            ),
            "retry_timeout_policy": config.retry_timeout_policy.model_copy(
                update={
                    "timeout_execution_enabled": False,
                    "retry_loop_enabled": False,
                    "sleep_backoff_enabled": False,
                }
            ),
            "error_response_draft": config.error_response_draft.model_copy(
                update={
                    "captures_live_response": False,
                    "wraps_transport_exception": False,
                    "contains_credential_material": False,
                }
            ),
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )


def _validate_endpoint_evidence_ref(
    config: KiwoomMockApiTransportDraftConfig,
    domains: dict[str, object],
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> None:
    endpoint = config.endpoint_evidence_ref
    validate_kiwoom_mock_api_transport_draft_metadata_safety(
        {
            "documented_method": endpoint.documented_method,
            "documented_path": endpoint.documented_path,
            "documented_category": endpoint.documented_category,
        },
        context="endpoint_evidence_ref",
    )
    expected_mock_domain = str(domains.get("mock_rest_domain", "")).strip()
    expected_prod_domain = str(domains.get("production_rest_domain", "")).strip()
    if endpoint.documented_mock_domain != expected_mock_domain:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED,
                "BLOCKING",
                "production domain execution remains blocked",
            )
        )
    if endpoint.documented_production_domain != expected_prod_domain:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED,
                "BLOCKING",
                "production domain evidence mismatch",
            )
        )
    if endpoint.executable or not endpoint.evidence_only:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT,
                "BLOCKING",
                "endpoint evidence refs must remain documentation-only",
            )
        )


def _validate_request_envelope(
    config: KiwoomMockApiTransportDraftConfig,
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> None:
    draft = config.request_envelope_draft
    validate_kiwoom_mock_api_transport_draft_metadata_safety(
        {
            "request_path": draft.request_path,
            "token_ref_id": draft.token_ref_id,
            "credential_ref_ids": draft.credential_ref_ids,
        },
        context="request_envelope_draft",
    )
    if draft.authorization_header_generation_available:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_AUTHORIZATION_HEADER_GENERATION_NOT_ALLOWED,
                "BLOCKING",
                "authorization header generation is not allowed",
            )
        )
    if draft.http_client_available:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED,
                "BLOCKING",
                "HTTP client creation is not allowed",
            )
        )
    if draft.http_session_available:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED,
                "BLOCKING",
                "HTTP session creation is not allowed",
            )
        )
    if draft.network_execution_enabled:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_NETWORK_CALL_NOT_ALLOWED,
                "BLOCKING",
                "network execution is not allowed",
            )
        )
    if draft.mock_domain_reference != "MOCK_DOMAIN_REF":
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED,
                "BLOCKING",
                "request envelope must remain mock-domain-only",
            )
        )
    if draft.documented_method != "POST":
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_API_CALL_NOT_ALLOWED,
                "BLOCKING",
                "HTTP method refs must remain non-executable metadata",
            )
        )


def _validate_transport_policy(
    config: KiwoomMockApiTransportDraftConfig,
    domains: dict[str, object],
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> None:
    policy = config.transport_policy
    if policy.allowed_mock_rest_domain != str(domains.get("mock_rest_domain", "")).strip():
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_PRODUCTION_DOMAIN_NOT_ALLOWED,
                "BLOCKING",
                "mock-domain-only policy mismatch",
            )
        )
    gap_entries.extend(
        [
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_TRANSPORT_MISSING_EXECUTABLE_TRANSPORT,
                "BLOCKING",
                "transport execution remains intentionally unimplemented",
            ),
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED,
                "REPORT_ONLY",
                "HTTP client creation remains blocked",
            ),
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_SESSION_NOT_ALLOWED,
                "REPORT_ONLY",
                "HTTP session creation remains blocked",
            ),
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_MOCKAPI_CALL_NOT_ALLOWED,
                "REPORT_ONLY",
                "mockapi execution remains blocked",
            ),
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_NETWORK_CALL_NOT_ALLOWED,
                "REPORT_ONLY",
                "network execution remains blocked",
            ),
        ]
    )


def _validate_retry_timeout_policy(
    config: KiwoomMockApiTransportDraftConfig,
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> None:
    policy = config.retry_timeout_policy
    if policy.timeout_execution_enabled or policy.retry_loop_enabled or policy.sleep_backoff_enabled:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_HTTP_CLIENT_NOT_ALLOWED,
                "BLOCKING",
                "retry/timeout policy must remain representation-only",
            )
        )


def _validate_error_response_draft(
    config: KiwoomMockApiTransportDraftConfig,
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> None:
    error_draft = config.error_response_draft
    if error_draft.captures_live_response or error_draft.wraps_transport_exception:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_NETWORK_CALL_NOT_ALLOWED,
                "BLOCKING",
                "error response draft must remain local and non-executable",
            )
        )
    if error_draft.contains_credential_material:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_RAW_SECRET_NOT_ALLOWED,
                "BLOCKING",
                "error response draft must not contain credential material",
            )
        )


def _validate_oauth_boundary_ref(
    oauth_draft_boundary_ref: str | None,
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
    findings: list[str],
) -> None:
    if oauth_draft_boundary_ref is None:
        gap_entries.append(
            (
                KiwoomMockApiTransportGapCategory.KIWOOM_MOCK_API_MISSING_INPUT,
                "BLOCKING",
                "oauth draft boundary dependency reference is required",
            )
        )
        return
    _validate_local_reference_path(oauth_draft_boundary_ref, "oauth_draft_boundary_ref")
    findings.append("oauth_draft_boundary_dependency=REFERENCE_ONLY")


def _build_safety_report(
    report: KiwoomMockApiTransportSafetyReport,
    findings: list[str],
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> KiwoomMockApiTransportSafetyReport:
    blocked = list(dict.fromkeys([*report.blocked_capabilities, *_BLOCKED_CAPABILITIES]))
    derived_findings = list(findings)
    derived_findings.extend(
        f"{category.value}:{severity}:{message}" for category, severity, message in gap_entries
    )
    return report.model_copy(update={"blocked_capabilities": blocked, "findings": derived_findings})


def _build_gap_report(
    report: KiwoomMockApiTransportGapReport,
    gap_entries: list[tuple[KiwoomMockApiTransportGapCategory, str, str]],
) -> KiwoomMockApiTransportGapReport:
    categories = list(dict.fromkeys(category for category, _, _ in gap_entries))
    gaps = list(dict.fromkeys(message for _, _, message in gap_entries))
    blocking_gap_count = sum(1 for _, severity, _ in gap_entries if severity == "BLOCKING")
    report_only_gap_count = sum(1 for _, severity, _ in gap_entries if severity == "REPORT_ONLY")
    return report.model_copy(
        update={
            "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS" if categories else report.gap_status,
            "gap_categories": categories,
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": gaps,
        }
    )


def _build_audit_records(
    audit_records: list[KiwoomMockApiTransportAuditRecord],
    config_id: str,
    oauth_draft_boundary_ref: str | None,
) -> list[KiwoomMockApiTransportAuditRecord]:
    built: list[KiwoomMockApiTransportAuditRecord] = []
    for record in audit_records:
        evidence_refs = list(record.evidence_refs)
        if oauth_draft_boundary_ref is not None:
            evidence_refs.append("OAUTH_DRAFT_BOUNDARY_REF_ONLY")
        evidence_refs.append(f"TRANSPORT_CONFIG:{config_id}")
        built.append(
            record.model_copy(
                update={
                    "created_at": datetime.now(timezone.utc),
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "evidence_refs": list(dict.fromkeys(evidence_refs)),
                }
            )
        )
    return built
