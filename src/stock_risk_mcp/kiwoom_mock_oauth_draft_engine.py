from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from stock_risk_mcp.kiwoom_mock_oauth_draft_guard import (
    validate_kiwoom_mock_oauth_draft_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_oauth_draft_models import (
    KiwoomMockOAuthAuditRecord,
    KiwoomMockOAuthDraftConfig,
    KiwoomMockOAuthGapCategory,
    KiwoomMockOAuthGapReport,
    KiwoomMockOAuthSafetyReport,
)


_BLOCKED_CAPABILITIES = [
    "TOKEN_ISSUE_EXECUTION_BLOCKED",
    "TOKEN_REVOKE_EXECUTION_BLOCKED",
    "TOKEN_REFRESH_BLOCKED",
    "TOKEN_STORAGE_BLOCKED",
    "AUTHORIZATION_HEADER_GENERATION_BLOCKED",
    "API_CALL_BLOCKED",
    "MOCKAPI_CALL_BLOCKED",
    "NETWORK_CALL_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "PRODUCTION_DOMAIN_EXECUTION_BLOCKED",
    "LIVE_PROD_BLOCKED",
    "CREDENTIAL_LOADING_BLOCKED",
    "ENVIRONMENT_READ_BLOCKED",
    "CREDENTIAL_FILE_READ_BLOCKED",
    "REAL_ACCOUNT_READ_BLOCKED",
    "REAL_ACCOUNT_MUTATION_BLOCKED",
    "REAL_ORDER_BLOCKED",
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


def run_kiwoom_mock_oauth_draft_boundary(
    config: KiwoomMockOAuthDraftConfig,
    *,
    explicit_opt_in_ack: bool = False,
    credential_boundary_ref: str | None = None,
) -> KiwoomMockOAuthDraftConfig:
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]] = []
    findings: list[str] = []
    domains = _load_domains()

    _validate_endpoint_refs(config, domains, gap_entries)
    _validate_token_drafts(config, gap_entries)
    _validate_lifecycle_policy(config, gap_entries)
    _validate_credential_boundary_ref(credential_boundary_ref, gap_entries, findings)
    _validate_explicit_opt_in(explicit_opt_in_ack, gap_entries, findings)

    findings.extend(
        [
            f"explicit_opt_in_acknowledged={'true' if explicit_opt_in_ack else 'false'}",
            "draft_bundle_built=true",
            "credential_ref_policy=REFERENCE_ONLY",
            "authorization_header_generation=false",
            "request_execution_enabled=false",
            "network_transport_created=false",
            "token_storage_created=false",
            "token_refresh_created=false",
            "token_value_materialized=false",
            "mock_endpoint_refs_mode=EVIDENCE_ONLY",
        ]
    )

    safety_report = _build_safety_report(config.safety_report, findings, gap_entries)
    gap_report = _build_gap_report(config.gap_report, gap_entries)
    audit_records = _build_audit_records(config.audit_records, config.config_id, credential_boundary_ref)

    return config.model_copy(
        update={
            "token_request_draft": config.token_request_draft.model_copy(
                update={
                    "credential_ref_only": True,
                    "authorization_header_available": False,
                    "request_execution_enabled": False,
                }
            ),
            "token_response_draft": config.token_response_draft.model_copy(
                update={
                    "stores_real_token": False,
                    "token_storage_enabled": False,
                    "token_refresh_enabled": False,
                }
            ),
            "token_revoke_draft": config.token_revoke_draft.model_copy(
                update={
                    "credential_ref_only": True,
                    "request_execution_enabled": False,
                }
            ),
            "token_lifecycle_policy": config.token_lifecycle_policy.model_copy(
                update={
                    "issue_execution_allowed": False,
                    "revoke_execution_allowed": False,
                    "refresh_execution_allowed": False,
                    "storage_execution_allowed": False,
                    "token_value_retained": False,
                }
            ),
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )


def _validate_endpoint_refs(
    config: KiwoomMockOAuthDraftConfig,
    domains: dict[str, object],
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
) -> None:
    expected_mock_domain = str(domains.get("mock_rest_domain", "")).strip()
    expected_prod_domain = str(domains.get("production_rest_domain", "")).strip()
    for endpoint in config.endpoint_refs:
        validate_kiwoom_mock_oauth_draft_metadata_safety(
            {
                "method": endpoint.method,
                "path": endpoint.path,
            },
            context="endpoint_ref",
        )
        if endpoint.domain != expected_mock_domain:
            gap_entries.append(
                (
                    KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_PRODUCTION_DOMAIN_NOT_ALLOWED,
                    "BLOCKING",
                    "production domain execution remains blocked",
                )
            )
        if endpoint.executable or not endpoint.evidence_only:
            gap_entries.append(
                (
                    KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
                    "BLOCKING",
                    "oauth endpoint refs must remain evidence-only and non-executable",
                )
            )
        if not endpoint.production_domain_blocked or expected_prod_domain != "https://api.kiwoom.com":
            gap_entries.append(
                (
                    KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_PRODUCTION_DOMAIN_NOT_ALLOWED,
                    "BLOCKING",
                    "production domain policy mismatch",
                )
            )


def _validate_token_drafts(
    config: KiwoomMockOAuthDraftConfig,
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
) -> None:
    if config.token_request_draft.request_execution_enabled or config.token_revoke_draft.request_execution_enabled:
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
                "BLOCKING",
                "oauth draft execution must remain disabled",
            )
        )
    if config.token_request_draft.authorization_header_available:
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_AUTH_HEADER_DETECTED,
                "BLOCKING",
                "authorization header generation is not allowed",
            )
        )
    if config.token_response_draft.stores_real_token:
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_TOKEN_VALUE_DETECTED,
                "BLOCKING",
                "real token values must not be stored",
            )
        )


def _validate_lifecycle_policy(
    config: KiwoomMockOAuthDraftConfig,
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
) -> None:
    if (
        config.token_lifecycle_policy.issue_execution_allowed
        or config.token_lifecycle_policy.revoke_execution_allowed
        or config.token_lifecycle_policy.refresh_execution_allowed
        or config.token_lifecycle_policy.storage_execution_allowed
        or config.token_lifecycle_policy.token_value_retained
    ):
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
                "BLOCKING",
                "token lifecycle policy must remain non-executable",
            )
        )


def _validate_credential_boundary_ref(
    credential_boundary_ref: str | None,
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
    findings: list[str],
) -> None:
    if credential_boundary_ref is None:
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_MISSING_INPUT,
                "BLOCKING",
                "credential boundary dependency reference is required",
            )
        )
        return
    _validate_local_reference_path(credential_boundary_ref, "credential_boundary_ref")
    findings.append("credential_boundary_dependency=REFERENCE_ONLY")


def _validate_explicit_opt_in(
    explicit_opt_in_ack: bool,
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
    findings: list[str],
) -> None:
    gap_entries.append(
        (
            KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
            "REPORT_ONLY",
            "v6.5 remains draft-only and does not allow executable oauth mode",
        )
    )
    if not explicit_opt_in_ack:
        gap_entries.append(
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_EXECUTION_MODE_NOT_ALLOWED,
                "BLOCKING",
                "explicit opt-in acknowledgement is required even for local draft assembly",
            )
        )
    else:
        findings.append("explicit_opt_in_gate=ACKNOWLEDGED_FOR_LOCAL_DRAFT_ONLY")

    gap_entries.extend(
        [
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_MISSING_EXECUTABLE_TRANSPORT,
                "REPORT_ONLY",
                "executable transport intentionally unimplemented",
            ),
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_MOCKAPI_CALL_NOT_ALLOWED,
                "REPORT_ONLY",
                "mockapi execution remains blocked",
            ),
            (
                KiwoomMockOAuthGapCategory.KIWOOM_MOCK_OAUTH_CREDENTIAL_FILE_REFERENCE_DETECTED,
                "REPORT_ONLY",
                "credential file loading remains intentionally unresolved and blocked",
            ),
        ]
    )


def _build_safety_report(
    base_report: KiwoomMockOAuthSafetyReport,
    findings: list[str],
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
) -> KiwoomMockOAuthSafetyReport:
    messages = [message for _, _, message in gap_entries]
    normalized_findings = sorted(set([*findings, *messages]))
    return base_report.model_copy(
        update={
            "blocked_capabilities": _BLOCKED_CAPABILITIES,
            "findings": normalized_findings,
        }
    )


def _build_gap_report(
    base_report: KiwoomMockOAuthGapReport,
    gap_entries: list[tuple[KiwoomMockOAuthGapCategory, str, str]],
) -> KiwoomMockOAuthGapReport:
    categories = [category for category, _, _ in gap_entries]
    gaps = [message for _, _, message in gap_entries]
    blocking_gap_count = sum(1 for _, severity, _ in gap_entries if severity == "BLOCKING")
    report_only_gap_count = sum(1 for _, severity, _ in gap_entries if severity == "REPORT_ONLY")
    return base_report.model_copy(
        update={
            "gap_status": "UNRESOLVED_IMPLEMENTATION_GAPS" if gap_entries else "NO_GAPS",
            "gap_categories": categories,
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": gaps,
        }
    )


def _build_audit_records(
    audit_records: list[KiwoomMockOAuthAuditRecord],
    config_id: str,
    credential_boundary_ref: str | None,
) -> list[KiwoomMockOAuthAuditRecord]:
    if audit_records:
        base = audit_records[0]
        return [
            base.model_copy(
                update={
                    "audit_record_id": f"{config_id}-AUDIT-EVALUATED",
                    "redaction_applied": True,
                    "contains_secret_material": False,
                    "evidence_refs": sorted(
                        {
                            *base.evidence_refs,
                            "KIWOOM-REST-EVIDENCE-PACK",
                            "KIWOOM-CAPABILITY-MATRIX",
                            "KIWOOM-MOCK-CREDENTIAL-BOUNDARY-PLAN",
                        }
                    ),
                }
            )
        ]
    return [
        KiwoomMockOAuthAuditRecord.model_validate(
            {
                "audit_record_id": f"{config_id}-AUDIT-EVALUATED",
                "created_at": datetime.now(timezone.utc).astimezone(),
                "source_path": credential_boundary_ref
                or "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
                "redaction_applied": True,
                "contains_secret_material": False,
                "evidence_refs": [
                    "KIWOOM-REST-EVIDENCE-PACK",
                    "KIWOOM-CAPABILITY-MATRIX",
                    "KIWOOM-MOCK-CREDENTIAL-BOUNDARY-PLAN",
                ],
            }
        )
    ]
