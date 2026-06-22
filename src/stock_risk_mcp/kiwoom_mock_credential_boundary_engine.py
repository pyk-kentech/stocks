from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from stock_risk_mcp.kiwoom_mock_credential_boundary_guard import (
    validate_kiwoom_mock_credential_boundary_metadata_safety,
)
from stock_risk_mcp.kiwoom_mock_credential_boundary_models import (
    KiwoomMockCredentialAuditRecord,
    KiwoomMockCredentialBoundaryConfig,
    KiwoomMockCredentialGapCategory,
    KiwoomMockCredentialGapReport,
    KiwoomMockCredentialRef,
    KiwoomMockCredentialSafetyReport,
    KiwoomMockDomainPolicy,
    KiwoomMockEnvironment,
    KiwoomMockExecutionMode,
    KiwoomMockOptInGate,
    KiwoomMockTokenBoundary,
)


_UNSAFE_GAP_MAP = (
    ("raw credential value", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
    ("environment read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED, "environment read not allowed"),
    ("credential file read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED, "credential file read not allowed"),
    ("token issue", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED, "token issue not allowed"),
    ("token revoke", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED, "token revoke not allowed"),
    ("mockapi call", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED, "mockapi call not allowed"),
    ("api call", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED, "api call not allowed"),
    ("websocket", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED, "websocket not allowed"),
    ("network", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED, "network call not allowed"),
    ("production domain execution", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED, "production domain execution not allowed"),
    ("real order", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED, "real order not allowed"),
    ("live trading", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED, "live trading not allowed"),
    ("account mutation", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED, "account mutation not allowed"),
    ("live/prod", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
    ("cloud llm", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
    ("local llm runtime", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
    ("parquet", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED, "parquet not allowed"),
)

_ALLOWED_ENV_NAMES = {
    "KIWOOM_MOCK_ONLY",
    "KIWOOM_MOCK_DRY_RUN",
    "KIWOOM_MOCK_EXPLICIT_OPT_IN",
    "KIWOOM_MOCK_APP_KEY_REF",
    "KIWOOM_MOCK_SECRET_KEY_REF",
    "KIWOOM_MOCK_ACCOUNT_REF",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_domains() -> dict[str, object]:
    matrix_path = _repo_root() / "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    return dict(matrix.get("domains", {}))


def run_kiwoom_mock_credential_boundary_evaluation(
    config: KiwoomMockCredentialBoundaryConfig,
) -> KiwoomMockCredentialBoundaryConfig:
    gap_entries: list[dict[str, str]] = []
    findings: list[str] = []
    domains = _load_domains()

    _evaluate_environment(config.environment, gap_entries, findings)
    _evaluate_credential_refs(config.credential_refs, gap_entries, findings)
    _evaluate_domain_policy(config.domain_policy, domains, gap_entries, findings)
    _evaluate_opt_in_gate(config.opt_in_gate, gap_entries, findings)
    _evaluate_token_boundary(config.token_boundary, domains, gap_entries, findings)
    findings.append(f"execution_mode_boundary={_execution_mode_boundary(config.execution_mode)}")
    findings.append("token_storage_policy=NOT_CREATED")
    findings.append("token_refresh_policy=POLICY_ONLY")
    findings.append("environment_policy_evaluated_symbolically=true")
    findings.append("credential_refs_loaded=false")
    findings.append("network_transport_created=false")

    safety_report = _build_safety_report(config.safety_report, gap_entries, findings)
    gap_report = _build_gap_report(config.gap_report, gap_entries)
    audit_records = _build_audit_records(config.audit_records, config.config_id)

    return config.model_copy(
        update={
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )


def _evaluate_environment(environment, gap_entries: list[dict[str, str]], findings: list[str]) -> None:
    if not isinstance(environment, KiwoomMockEnvironment):
        gap_entries.append(_gap("missing-environment", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_ENVIRONMENT, "BLOCKING", "missing environment policy"))
        return
    env_names = {
        environment.mock_only_env_name,
        environment.dry_run_env_name,
        environment.explicit_opt_in_env_name,
        environment.app_key_ref_env_name,
        environment.secret_key_ref_env_name,
        environment.account_ref_env_name,
    }
    if env_names != _ALLOWED_ENV_NAMES:
        gap_entries.append(_gap("unsafe-environment-policy", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED, "BLOCKING", "unsafe environment policy"))
    if environment.reads_environment:
        gap_entries.append(_gap("environment-read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED, "BLOCKING", "environment read not allowed"))
    findings.append("environment_policy=SYMBOLIC_ONLY")


def _evaluate_credential_refs(
    credential_refs: list[KiwoomMockCredentialRef] | object,
    gap_entries: list[dict[str, str]],
    findings: list[str],
) -> None:
    if not isinstance(credential_refs, list) or not credential_refs:
        gap_entries.append(_gap("missing-input", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_INPUT, "BLOCKING", "missing credential refs"))
        return
    for index, credential_ref in enumerate(credential_refs):
        if not isinstance(credential_ref, KiwoomMockCredentialRef):
            gap_entries.append(_gap(f"credential-ref-{index}-invalid", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "BLOCKING", "invalid credential ref"))
            continue
        if credential_ref.reference_name not in _ALLOWED_ENV_NAMES:
            gap_entries.append(_gap(f"{credential_ref.credential_ref_id}-secret", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "BLOCKING", "symbolic credential ref required"))
        if credential_ref.loaded:
            gap_entries.append(_gap(f"{credential_ref.credential_ref_id}-loaded", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CREDENTIAL_LOADING_NOT_ALLOWED, "BLOCKING", "credential loading not allowed"))
        if credential_ref.secret_material_present:
            gap_entries.append(_gap(f"{credential_ref.credential_ref_id}-secret-present", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_UNREDACTED_SECRET_NOT_ALLOWED, "BLOCKING", "unredacted secret not allowed"))
        if credential_ref.reads_credential_file:
            gap_entries.append(_gap(f"{credential_ref.credential_ref_id}-file-read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED, "BLOCKING", "credential file read not allowed"))
        _append_text_hazards(credential_ref.reference_name, f"{credential_ref.credential_ref_id}-reference", gap_entries)
        _append_text_hazards(credential_ref.source_label, f"{credential_ref.credential_ref_id}-source", gap_entries)
    findings.append("credential_ref_policy=SYMBOLIC_REFS_ONLY")


def _evaluate_domain_policy(
    domain_policy,
    domains: dict[str, object],
    gap_entries: list[dict[str, str]],
    findings: list[str],
) -> None:
    if not isinstance(domain_policy, KiwoomMockDomainPolicy):
        gap_entries.append(_gap("missing-domain-policy", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_DOMAIN_POLICY, "BLOCKING", "missing domain policy"))
        return
    expected_mock_rest = str(domains.get("mock_rest_domain", "")).strip()
    expected_prod_rest = str(domains.get("production_rest_domain", "")).strip()
    expected_mock_ws = str(domains.get("mock_websocket_domain", "")).strip()
    expected_prod_ws = str(domains.get("production_websocket_domain", "")).strip()
    if domain_policy.allowed_mock_rest_domain != expected_mock_rest:
        gap_entries.append(_gap(f"{domain_policy.domain_policy_id}-mock-domain", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED, "BLOCKING", "mock domain is required"))
    if (
        domain_policy.forbidden_production_rest_domain != expected_prod_rest
        or domain_policy.forbidden_production_websocket_domain != expected_prod_ws
        or domain_policy.production_domain_execution_allowed
    ):
        gap_entries.append(_gap(f"{domain_policy.domain_policy_id}-production-domain", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PRODUCTION_DOMAIN_NOT_ALLOWED, "BLOCKING", "production domain execution not allowed"))
    if domain_policy.allowed_mock_websocket_domain != expected_mock_ws:
        gap_entries.append(_gap(f"{domain_policy.domain_policy_id}-mock-websocket", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCK_DOMAIN_REQUIRED, "REPORT_ONLY", "mock websocket domain metadata should remain documented"))
    if "prod" in domain_policy.allowed_mock_websocket_domain.lower() or "live" in domain_policy.allowed_mock_websocket_domain.lower():
        _append_text_hazards(domain_policy.allowed_mock_websocket_domain, f"{domain_policy.domain_policy_id}-ws", gap_entries)
    findings.append("domain_policy=MOCK_ONLY_BLOCKS_PRODUCTION")


def _evaluate_opt_in_gate(opt_in_gate, gap_entries: list[dict[str, str]], findings: list[str]) -> None:
    if not isinstance(opt_in_gate, KiwoomMockOptInGate):
        gap_entries.append(_gap("missing-opt-in-gate", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_OPT_IN_GATE, "BLOCKING", "missing opt-in gate"))
        return
    if opt_in_gate.gate_state != "BLOCKED_DEFAULT":
        gap_entries.append(_gap(f"{opt_in_gate.opt_in_gate_id}-default", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED, "BLOCKING", "explicit opt-in gate must remain blocked by default"))
    if opt_in_gate.explicit_opt_in_present or opt_in_gate.mock_execution_allowed_now or not opt_in_gate.dry_run_only:
        gap_entries.append(_gap(f"{opt_in_gate.opt_in_gate_id}-opt-in", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_EXPLICIT_OPT_IN_REQUIRED, "BLOCKING", "explicit opt-in remains future-only"))
    findings.append("opt_in_gate=DISABLED_BY_DEFAULT")


def _evaluate_token_boundary(
    token_boundary,
    domains: dict[str, object],
    gap_entries: list[dict[str, str]],
    findings: list[str],
) -> None:
    if not isinstance(token_boundary, KiwoomMockTokenBoundary):
        gap_entries.append(_gap("missing-input-token-boundary", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MISSING_INPUT, "BLOCKING", "missing token boundary"))
        return
    if token_boundary.documented_issue_endpoint_path != str(domains.get("oauth_token_endpoint", "")).strip():
        gap_entries.append(_gap(f"{token_boundary.token_boundary_id}-issue-policy", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED, "REPORT_ONLY", "token issue policy path mismatch"))
    if token_boundary.documented_revoke_endpoint_path != str(domains.get("oauth_revoke_endpoint", "")).strip():
        gap_entries.append(_gap(f"{token_boundary.token_boundary_id}-revoke-policy", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED, "REPORT_ONLY", "token revoke policy path mismatch"))
    if token_boundary.issue_allowed_now or token_boundary.token_issue_attempted:
        gap_entries.append(_gap(f"{token_boundary.token_boundary_id}-issue", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED, "BLOCKING", "token issue not allowed"))
    if token_boundary.revoke_allowed_now or token_boundary.token_revoke_attempted:
        gap_entries.append(_gap(f"{token_boundary.token_boundary_id}-revoke", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED, "BLOCKING", "token revoke not allowed"))
    findings.append("token_boundary=POLICY_ONLY")


def _execution_mode_boundary(mode: KiwoomMockExecutionMode | object) -> str:
    normalized = getattr(mode, "value", mode)
    if normalized == KiwoomMockExecutionMode.KIWOOM_MOCK_DISABLED.value:
        return "DRAFT_ONLY"
    if normalized == KiwoomMockExecutionMode.KIWOOM_MOCK_DRY_RUN.value:
        return "DRY_RUN_BOUNDARY_ONLY"
    return "FUTURE_OPT_IN_MOCK_ONLY"


def _build_safety_report(
    base_report: KiwoomMockCredentialSafetyReport,
    gap_entries: list[dict[str, str]],
    findings: list[str],
) -> KiwoomMockCredentialSafetyReport:
    blocking = any(entry["severity"] == "BLOCKING" for entry in gap_entries)
    normalized_findings = sorted({*findings, *(entry["message"] for entry in gap_entries)})
    return base_report.model_copy(update={"blocked": blocking, "findings": normalized_findings})


def _build_gap_report(
    base_report: KiwoomMockCredentialGapReport,
    gap_entries: list[dict[str, str]],
) -> KiwoomMockCredentialGapReport:
    categories = [KiwoomMockCredentialGapCategory(entry["category"]) for entry in gap_entries]
    blocking_gap_count = sum(1 for entry in gap_entries if entry["severity"] == "BLOCKING")
    report_only_gap_count = sum(1 for entry in gap_entries if entry["severity"] == "REPORT_ONLY")
    gap_status = "NO_GAPS" if not gap_entries else "GAPS_PRESENT"
    messages = [entry["message"] for entry in gap_entries]
    return base_report.model_copy(
        update={
            "gap_status": gap_status,
            "gap_categories": categories,
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": messages,
        }
    )


def _build_audit_records(
    audit_records: list[KiwoomMockCredentialAuditRecord] | object,
    config_id: str,
) -> list[KiwoomMockCredentialAuditRecord]:
    if isinstance(audit_records, list) and audit_records and isinstance(audit_records[0], KiwoomMockCredentialAuditRecord):
        base = audit_records[0]
        return [
            base.model_copy(
                update={
                    "audit_record_id": f"{config_id}-AUDIT-EVALUATED",
                }
            )
        ]
    return [
        KiwoomMockCredentialAuditRecord.model_validate(
            {
                "audit_record_id": f"{config_id}-AUDIT-EVALUATED",
                "created_at": datetime.now(timezone.utc).astimezone(),
                "source_path": "docs/superpowers/plans/2026-06-18-kiwoom-mock-credential-environment-boundary-design.md",
                "source_manifest_ids": [],
            }
        )
    ]


def _gap(gap_id: str, category: KiwoomMockCredentialGapCategory, severity: str, message: str) -> dict[str, str]:
    return {"gap_id": gap_id, "category": category.value, "severity": severity, "message": message}


def _unsafe_gap(gap_id: str, label: str) -> dict[str, str]:
    for unsafe_label, category, message in _UNSAFE_GAP_MAP:
        if label == unsafe_label:
            return _gap(gap_id, category, "BLOCKING", message)
    return _gap(gap_id, KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "BLOCKING", label)


def _append_text_hazards(text: str, prefix: str, gap_entries: list[dict[str, str]]) -> None:
    lowered = text.lower()
    checks = (
        ("appkey", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("app_key_value", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("secret_key_value", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("access_token", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("authorization", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("bearer", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("account_number", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("acct_no", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("password", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("cert", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("private_key", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_SECRET_VALUE_NOT_ALLOWED, "raw credential value not allowed"),
        ("environment_read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ENVIRONMENT_READ_NOT_ALLOWED, "environment read not allowed"),
        ("credential_file_read", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CREDENTIAL_FILE_READ_NOT_ALLOWED, "credential file read not allowed"),
        ("token_issue", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_ISSUE_NOT_ALLOWED, "token issue not allowed"),
        ("token_revoke", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_TOKEN_REVOKE_NOT_ALLOWED, "token revoke not allowed"),
        ("api_call", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_API_CALL_NOT_ALLOWED, "api call not allowed"),
        ("mockapi_call", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_MOCKAPI_CALL_NOT_ALLOWED, "mockapi call not allowed"),
        ("websocket", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_WEBSOCKET_NOT_ALLOWED, "websocket not allowed"),
        ("network", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_NETWORK_CALL_NOT_ALLOWED, "network call not allowed"),
        ("real_order", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_REAL_ORDER_NOT_ALLOWED, "real order not allowed"),
        ("live_trading", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_TRADING_NOT_ALLOWED, "live trading not allowed"),
        ("account_mutation", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_ACCOUNT_MUTATION_NOT_ALLOWED, "account mutation not allowed"),
        ("prod", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
        ("live", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
        ("gemini", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
        ("openai", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
        ("claude", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
        ("ollama", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
        ("vllm", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
        ("llama", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
        ("parquet", KiwoomMockCredentialGapCategory.KIWOOM_CREDENTIAL_PARQUET_NOT_ALLOWED, "parquet not allowed"),
    )
    for marker, category, message in checks:
        if marker in lowered:
            gap_entries.append(_gap(f"{prefix}-{category.value}", category, "BLOCKING", message))
