from __future__ import annotations

from stock_risk_mcp.controlled_execution_models import (
    ControlledExecutionAdapterCapabilityReport,
    ControlledExecutionAdapterCapabilityRow,
    ControlledExecutionAdapterStatus,
    ControlledExecutionCredentialPolicy,
    ControlledExecutionMode,
    ControlledExecutionPipelineInput,
    ControlledExecutionProvider,
)


def build_controlled_execution_adapter_capability_report(
    pipeline_input: ControlledExecutionPipelineInput,
) -> ControlledExecutionAdapterCapabilityReport:
    exact_kiwoom_schema = bool(pipeline_input.adapter_evidence.get("kiwoom_exact_schema"))
    exact_ls_schema = bool(pipeline_input.adapter_evidence.get("ls_exact_schema"))
    rows = [
        ControlledExecutionAdapterCapabilityRow(
            provider=ControlledExecutionProvider.LOCAL_MOCK,
            adapter_status=ControlledExecutionAdapterStatus.MOCK_READY,
            credential_policy=ControlledExecutionCredentialPolicy.MOCK_ONLY,
            exact_schema_evidence_present=True,
            allowlisted=True,
            notes="local mock execution adapter is supported",
        ),
        ControlledExecutionAdapterCapabilityRow(
            provider=ControlledExecutionProvider.DRY_RUN,
            adapter_status=ControlledExecutionAdapterStatus.DRY_RUN_READY,
            credential_policy=ControlledExecutionCredentialPolicy.NOT_REQUIRED,
            exact_schema_evidence_present=True,
            allowlisted=True,
            notes="dry-run no-broker adapter is supported",
        ),
        ControlledExecutionAdapterCapabilityRow(
            provider=ControlledExecutionProvider.KIWOOM,
            adapter_status=ControlledExecutionAdapterStatus.LIVE_BOUNDARY_BLOCKED_DEFAULT if exact_kiwoom_schema else ControlledExecutionAdapterStatus.ADAPTER_SCHEMA_GAP,
            credential_policy=ControlledExecutionCredentialPolicy.KEY_REF_ONLY,
            exact_schema_evidence_present=exact_kiwoom_schema,
            allowlisted=bool(pipeline_input.adapter_evidence.get("kiwoom_allowlisted")),
            notes="kiwoom live boundary remains blocked by default",
        ),
        ControlledExecutionAdapterCapabilityRow(
            provider=ControlledExecutionProvider.LS,
            adapter_status=ControlledExecutionAdapterStatus.LIVE_BOUNDARY_BLOCKED_DEFAULT if exact_ls_schema else ControlledExecutionAdapterStatus.ADAPTER_SCHEMA_GAP,
            credential_policy=ControlledExecutionCredentialPolicy.KEY_REF_ONLY,
            exact_schema_evidence_present=exact_ls_schema,
            allowlisted=bool(pipeline_input.adapter_evidence.get("ls_allowlisted")),
            notes="ls live boundary remains blocked by default",
        ),
    ]
    return ControlledExecutionAdapterCapabilityReport(
        report_id=f"{pipeline_input.pipeline_id}-ADAPTER-CAPABILITY-REPORT",
        mode=pipeline_input.mode,
        adapter_rows=rows,
        blocked_submit_preview={
            "provider": pipeline_input.provider.value,
            "instrument_id": pipeline_input.instrument_id,
            "mode": pipeline_input.mode.value,
            "blocked": True,
            "non_executable": True,
        },
    )
