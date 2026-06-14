import pytest

from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomCredentials,
    KiwoomRealNetworkConfig,
)
from stock_risk_mcp.kiwoom_real_readonly_transport import (
    FakeKiwoomTokenProvider,
    KiwoomRealReadOnlyPolicyError,
    RealKiwoomReadOnlyHttpTransport,
)
from stock_risk_mcp.order_intent import ExecutionMode, RiskGateDecision
from tests.test_order_risk_gate import _intent


class NoCallHttpClient:
    def post(self, url, headers, body, timeout_seconds):
        raise AssertionError("account-read checkpoint must not call HTTP")


def test_v218_checkpoint_keeps_manifest_account_endpoints_runtime_disabled() -> None:
    endpoints = {
        item.api_id: item
        for item in load_kiwoom_official_manifest().endpoints
        if item.read_write_class == KiwoomOfficialEndpointClass.ACCOUNT_READ
    }

    assert set(endpoints) == {"kt00001", "kt00007", "kt00018"}
    assert all(item.requires_account for item in endpoints.values())
    assert all(not item.runtime_allowed_in_current_version for item in endpoints.values())


@pytest.mark.parametrize("api_id", ["kt00001", "kt00007", "kt00018"])
def test_v218_checkpoint_blocks_account_endpoints_before_http(api_id: str) -> None:
    transport = RealKiwoomReadOnlyHttpTransport(
        KiwoomRealNetworkConfig(enabled=True),
        KiwoomCredentials(
            appkey="fake-app",
            secretkey="fake-secret",
            source=KiwoomCredentialSource.ENV,
        ),
        FakeKiwoomTokenProvider(),
        NoCallHttpClient(),
    )

    with pytest.raises(KiwoomRealReadOnlyPolicyError):
        transport.post(api_id, {})


def test_v218_checkpoint_does_not_enable_live_execution() -> None:
    intent = _intent()
    risk_decision = RiskGateDecision(
        order_intent_id=intent.order_intent_id,
        approved=True,
        decision="APPROVED",
    )

    decision = evaluate_execution_gate(intent, risk_decision, ExecutionMode.LIVE, False)

    assert not decision.approved
    assert decision.decision == "BLOCKED"
