from __future__ import annotations

from stock_risk_mcp.local_model_runtime_adapter import MockLocalRuntimeAdapter
from stock_risk_mcp.local_model_runtime_guard import detect_unsafe_runtime_output, validate_prompt_task_alignment
from stock_risk_mcp.local_model_runtime_models import (
    LOCAL_MODEL_RUNTIME_METADATA,
    LocalModelBackendType,
    LocalModelCandidatesFixture,
    LocalModelCandidatesResult,
    LocalModelRuntimeFixture,
    LocalModelRuntimeResult,
    LocalModelRuntimeStatus,
)


def _base_metadata(mock_runtime_used: bool) -> dict:
    return {**LOCAL_MODEL_RUNTIME_METADATA, "mock_runtime_used": mock_runtime_used}


def _result(fixture: LocalModelRuntimeFixture, fixture_checksum: str, status: LocalModelRuntimeStatus, **kwargs) -> LocalModelRuntimeResult:
    return LocalModelRuntimeResult(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        backend_type=fixture.backend.backend_type,
        status=status,
        adapter_name=fixture.backend.adapter_name,
        model_name=fixture.backend.model_name,
        task_type=fixture.request.task_type,
        capability_metadata=fixture.backend.capabilities.model_dump(mode="json"),
        timeout_applied_ms=fixture.runtime_limits.timeout_ms,
        resource_limits_applied=fixture.runtime_limits.model_dump(mode="json"),
        audit_metadata={
            "backend_type": fixture.backend.backend_type.value,
            "adapter_name": fixture.backend.adapter_name,
            "model_name": fixture.backend.model_name,
            "model_version": fixture.backend.model_version,
        },
        **kwargs,
    )


def list_local_model_candidates(fixture: LocalModelCandidatesFixture, fixture_checksum: str) -> LocalModelCandidatesResult:
    return LocalModelCandidatesResult(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        candidate_count=len(fixture.candidates),
        candidates=fixture.candidates,
    )


def run_local_model_runtime_check_fixture(fixture: LocalModelRuntimeFixture, fixture_checksum: str) -> LocalModelRuntimeResult:
    validate_prompt_task_alignment(fixture)
    if fixture.backend.backend_type == LocalModelBackendType.DISABLED:
        return _result(
            fixture,
            fixture_checksum,
            LocalModelRuntimeStatus.BACKEND_DISABLED,
            refusal_reason="local model runtime disabled",
            health_metadata={
                "health_status": "DISABLED",
                "adapter_name": fixture.backend.adapter_name,
                "backend_type": fixture.backend.backend_type.value,
                "configured_model_name": fixture.backend.model_name,
                "mock_mode": False,
                "timeout_supported": fixture.backend.capabilities.supports_timeout_budget,
                "resource_limits_supported": fixture.backend.capabilities.supports_resource_budget,
                "structured_output_supported": fixture.backend.capabilities.supports_structured_json_output,
                "local_only_asserted": True,
                "network_required": False,
            },
            metadata_json=_base_metadata(False),
        )
    if fixture.backend.backend_type == LocalModelBackendType.MOCK_LOCAL_RUNTIME:
        health = MockLocalRuntimeAdapter().health_check(fixture)
        return _result(
            fixture,
            fixture_checksum,
            LocalModelRuntimeStatus.MOCK_RUNTIME_READY,
            health_metadata=health,
            metadata_json=_base_metadata(True),
        )
    return _result(
        fixture,
        fixture_checksum,
        LocalModelRuntimeStatus.UNIMPLEMENTED_BACKEND_REJECTED,
        refusal_reason=f"{fixture.backend.backend_type.value} not implemented in v3.9",
        health_metadata={
            "health_status": "REJECTED",
            "adapter_name": fixture.backend.adapter_name,
            "backend_type": fixture.backend.backend_type.value,
            "configured_model_name": fixture.backend.model_name,
            "mock_mode": False,
            "timeout_supported": fixture.backend.capabilities.supports_timeout_budget,
            "resource_limits_supported": fixture.backend.capabilities.supports_resource_budget,
            "structured_output_supported": fixture.backend.capabilities.supports_structured_json_output,
            "local_only_asserted": True,
            "network_required": False,
        },
        metadata_json=_base_metadata(False),
    )


def run_local_model_advisory_dry_run_fixture(fixture: LocalModelRuntimeFixture, fixture_checksum: str) -> LocalModelRuntimeResult:
    validate_prompt_task_alignment(fixture)
    if fixture.backend.backend_type == LocalModelBackendType.DISABLED:
        return _result(
            fixture,
            fixture_checksum,
            LocalModelRuntimeStatus.BACKEND_DISABLED,
            refusal_reason="local model runtime disabled",
            metadata_json=_base_metadata(False),
        )
    if fixture.backend.backend_type != LocalModelBackendType.MOCK_LOCAL_RUNTIME:
        return _result(
            fixture,
            fixture_checksum,
            LocalModelRuntimeStatus.UNIMPLEMENTED_BACKEND_REJECTED,
            refusal_reason=f"{fixture.backend.backend_type.value} not implemented in v3.9",
            metadata_json=_base_metadata(False),
        )
    payload = MockLocalRuntimeAdapter().run_advisory(fixture)
    unsafe_reason = detect_unsafe_runtime_output("\n".join([payload.summary_text, *payload.bullet_points, *payload.risk_labels]))
    if unsafe_reason:
        return _result(
            fixture,
            fixture_checksum,
            LocalModelRuntimeStatus.UNSAFE_OUTPUT_REJECTED,
            refusal_reason=unsafe_reason,
            metadata_json=_base_metadata(True),
        )
    return _result(
        fixture,
        fixture_checksum,
        LocalModelRuntimeStatus.ADVISORY_RESPONSE,
        summary_text=payload.summary_text,
        bullet_points=payload.bullet_points,
        risk_labels=payload.risk_labels,
        metadata_json=_base_metadata(True),
    )
