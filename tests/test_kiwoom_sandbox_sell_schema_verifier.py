from stock_risk_mcp.kiwoom_official_manifest import KiwoomOfficialEndpointClass
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_sell_schema import SandboxSellSchemaVerificationStatus
from stock_risk_mcp.kiwoom_sandbox_sell_schema_verifier import KiwoomSandboxSellSchemaVerifier


def test_current_repository_sell_schema_is_unverified_and_offline():
    report = KiwoomSandboxSellSchemaVerifier().verify()

    assert report.status == SandboxSellSchemaVerificationStatus.UNVERIFIED
    assert report.endpoint_id == "kt10000"
    assert report.endpoint_classification == KiwoomOfficialEndpointClass.ORDER.value
    assert "sell_side_value" in report.missing_fields
    assert "symbol_field" in report.missing_fields
    assert report.metadata_json["network_called"] is False
    assert report.metadata_json["credentials_read"] is False
    assert report.metadata_json["token_requested"] is False


def test_unofficial_mapping_is_blocked_instead_of_treated_as_evidence():
    report = KiwoomSandboxSellSchemaVerifier().verify(
        field_mapping={"sell_side_value": "guessed-value"},
        evidence_source="unofficial-wrapper",
    )

    assert report.status == SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
    assert report.blocked_reason == "UNOFFICIAL_SELL_SCHEMA_ASSUMPTION_BLOCKED"


def test_non_order_and_websocket_endpoints_are_rejected():
    verifier = KiwoomSandboxSellSchemaVerifier()

    readonly = verifier.verify(endpoint_id="ka10001")
    websocket = verifier.verify(endpoint_id="ka10171")
    unknown = verifier.verify(endpoint_id="missing")

    assert readonly.status == SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
    assert websocket.status == SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
    assert unknown.status == SandboxSellSchemaVerificationStatus.MISSING_REQUIRED_FIELD


def test_prod_environment_is_always_blocked():
    report = KiwoomSandboxSellSchemaVerifier().verify(
        environment=KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED,
    )

    assert report.status == SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
    assert report.blocked_reason == "PROD_SELL_SCHEMA_VERIFICATION_BLOCKED"


def test_mapping_input_is_blocked_until_committed_official_schema_source_exists():
    report = KiwoomSandboxSellSchemaVerifier().verify(
        field_mapping={"side_field": "official-side", "buy_side_value": "official-buy"},
    )

    assert report.status == SandboxSellSchemaVerificationStatus.BLOCKED_UNOFFICIAL_ASSUMPTION
    assert report.blocked_reason == "UNOFFICIAL_SELL_SCHEMA_ASSUMPTION_BLOCKED"
