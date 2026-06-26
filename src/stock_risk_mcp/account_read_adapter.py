from __future__ import annotations

from stock_risk_mcp.account_read_models import (
    AccountReadCredentialPolicy,
    AccountReadExecutionDecision,
    AccountReadMode,
    AccountReadPipelineInput,
    AccountReadProvider,
    AccountReadProviderCapabilityReport,
    AccountReadProviderCapabilityRow,
    AccountReadProviderCapabilityStatus,
    AccountReadReadinessStatus,
    AccountReadRequestPreview,
    AccountReadSnapshot,
)


def build_account_read_provider_capability_report() -> AccountReadProviderCapabilityReport:
    rows = [
        AccountReadProviderCapabilityRow(
            provider=AccountReadProvider.LOCAL_MANUAL,
            capability_status=AccountReadProviderCapabilityStatus.MANUAL_FIXTURE_ONLY,
            credential_policy=AccountReadCredentialPolicy.NOT_REQUIRED,
            notes="local manual snapshot fixtures are supported",
        ),
        AccountReadProviderCapabilityRow(
            provider=AccountReadProvider.LOCAL_MOCK,
            capability_status=AccountReadProviderCapabilityStatus.MOCKED_ADAPTER_READY,
            credential_policy=AccountReadCredentialPolicy.MOCK_ONLY,
            notes="mocked adapter parsing is supported",
        ),
        AccountReadProviderCapabilityRow(
            provider=AccountReadProvider.REDACTED_CAPTURE,
            capability_status=AccountReadProviderCapabilityStatus.SCHEMA_READY_READONLY,
            credential_policy=AccountReadCredentialPolicy.NOT_REQUIRED,
            notes="redacted captures can be normalized locally",
        ),
        AccountReadProviderCapabilityRow(
            provider=AccountReadProvider.KIWOOM,
            capability_status=AccountReadProviderCapabilityStatus.OPT_IN_REAL_READONLY_BOUNDARY,
            credential_policy=AccountReadCredentialPolicy.KEY_REF_ONLY,
            exact_api_evidence_present=True,
            notes="request preview and gate only; no real execution in v12",
        ),
        AccountReadProviderCapabilityRow(
            provider=AccountReadProvider.LS,
            capability_status=AccountReadProviderCapabilityStatus.PROVIDER_SETUP_REQUIRED,
            credential_policy=AccountReadCredentialPolicy.KEY_REF_ONLY,
            notes="provider setup required; v12 supports preview and local fixtures only",
        ),
    ]
    return AccountReadProviderCapabilityReport(
        report_id="ACCOUNT-READ-PROVIDER-CAPABILITY-REPORT",
        readiness_status=AccountReadReadinessStatus.ACCOUNT_READ_PREVIEW_READY,
        capability_rows=rows,
    )


def build_account_read_request_preview(
    pipeline_input: AccountReadPipelineInput,
) -> AccountReadRequestPreview:
    provider = pipeline_input.provider
    mode = pipeline_input.mode
    credential_policy = (
        AccountReadCredentialPolicy.KEY_REF_ONLY
        if provider in {AccountReadProvider.KIWOOM, AccountReadProvider.LS}
        else AccountReadCredentialPolicy.NOT_REQUIRED
    )
    request_path = f"/providers/{provider.value.lower()}/account/positions"
    notes = ["preview only", "read-only contract"]
    readiness = AccountReadReadinessStatus.ACCOUNT_READ_PREVIEW_READY
    can_execute_real_read = False
    exact_evidence = provider == AccountReadProvider.KIWOOM
    if mode != AccountReadMode.OPT_IN_REAL_READONLY_BOUNDARY:
        notes.append("fixture-backed canonical snapshot")
    else:
        notes.append("real boundary remains blocked in v12")
        readiness = AccountReadReadinessStatus.ACCOUNT_READ_BLOCKED_DEFAULT
    return AccountReadRequestPreview(
        preview_id=f"{pipeline_input.pipeline_id}-PREVIEW",
        provider=provider,
        mode=mode,
        readiness_status=readiness,
        request_path=request_path,
        request_method="GET",
        credential_policy=credential_policy,
        account_ref=pipeline_input.snapshot_fixture.metadata.account_ref if pipeline_input.snapshot_fixture else "REDACTED-UNAVAILABLE",
        requires_opt_in=True,
        can_execute_real_read=can_execute_real_read,
        exact_api_evidence_present=exact_evidence,
        query_params={"response_mode": "preview", "read_only": True},
        header_keys=["X-KEY-REF"],
        notes=notes,
    )


def build_account_read_execution_decision(
    pipeline_input: AccountReadPipelineInput,
    readiness_status: AccountReadReadinessStatus,
    findings: list[str],
) -> AccountReadExecutionDecision:
    blocked_reasons = list(findings)
    approved = False
    if pipeline_input.mode == AccountReadMode.OPT_IN_REAL_READONLY_BOUNDARY:
        blocked_reasons.append("REAL_EXECUTION_DISABLED_IN_V12")
    return AccountReadExecutionDecision(
        decision_id=f"{pipeline_input.pipeline_id}-DECISION",
        provider=pipeline_input.provider,
        readiness_status=readiness_status,
        approved=approved,
        blocked_reasons=blocked_reasons,
    )


def parse_account_read_snapshot(snapshot: AccountReadSnapshot) -> AccountReadSnapshot:
    return AccountReadSnapshot.model_validate(snapshot.model_dump(mode="json"))
