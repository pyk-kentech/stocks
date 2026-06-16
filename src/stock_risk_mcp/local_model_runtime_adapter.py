from __future__ import annotations

from dataclasses import dataclass

from stock_risk_mcp.local_model_runtime_models import LocalModelRuntimeFixture


@dataclass(frozen=True)
class MockRuntimePayload:
    summary_text: str
    bullet_points: list[str]
    risk_labels: list[str]


class MockLocalRuntimeAdapter:
    adapter_name = "mock-local-runtime"

    def health_check(self, fixture: LocalModelRuntimeFixture) -> dict:
        return {
            "health_status": "READY",
            "adapter_name": fixture.backend.adapter_name,
            "backend_type": fixture.backend.backend_type.value,
            "configured_model_name": fixture.backend.model_name,
            "mock_mode": True,
            "timeout_supported": fixture.backend.capabilities.supports_timeout_budget,
            "resource_limits_supported": fixture.backend.capabilities.supports_resource_budget,
            "structured_output_supported": fixture.backend.capabilities.supports_structured_json_output,
            "local_only_asserted": True,
            "network_required": False,
        }

    def run_advisory(self, fixture: LocalModelRuntimeFixture) -> MockRuntimePayload:
        return MockRuntimePayload(
            summary_text=fixture.mock_response.response_text,
            bullet_points=list(fixture.mock_response.bullet_points),
            risk_labels=list(fixture.mock_response.risk_labels),
        )
