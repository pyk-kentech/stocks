import json

import pytest

from stock_risk_mcp.kiwoom_mock_adapter_engine import (
    load_kiwoom_mock_capability_matrix,
    run_kiwoom_mock_adapter_draft_mapping,
)
from stock_risk_mcp.kiwoom_mock_adapter_models import KiwoomMockAdapterInput
from tests.test_kiwoom_mock_adapter_models import kiwoom_mock_adapter_fixture_payload


def _build_input(payload=None):
    return KiwoomMockAdapterInput.model_validate(payload or kiwoom_mock_adapter_fixture_payload())


def test_evidence_backed_capability_validation_success_path():
    result = run_kiwoom_mock_adapter_draft_mapping(_build_input())
    assert result.capability_ref.evidence_endpoint_ref == "KT10000"
    assert result.capability_ref.mock_domain == "https://mockapi.kiwoom.com"


def test_missing_capability_ref_gap():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["capability_ref"]["supported_order_types"] = []
    with pytest.raises(ValueError, match="unsupported order type"):
        _build_input(payload)


def test_missing_broker_mock_order_intent_ref_gap():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["source_broker_mock_order_intent_ref_id"] = ""
    with pytest.raises(ValueError, match="source_broker_mock_order_intent_ref_id must not be blank"):
        _build_input(payload)


def test_missing_evidence_endpoint_ref_gap():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["capability_ref"]["evidence_endpoint_ref"] = "KT99999"
    with pytest.raises(ValueError, match="supported official order endpoint|unsupported capability"):
        _build_input(payload)


def test_unsupported_capability_gap():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["capability_ref"]["capability_ref_id"] = "DOMESTIC_STOCK_ORDER_EXECUTE_LIVE"
    with pytest.raises(ValueError, match="unsupported capability"):
        _build_input(payload)


def test_capability_requiring_actual_api_call_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["capability_ref"]["evidence_endpoint_ref"] = "OAUTH2_TOKEN"
    with pytest.raises(ValueError, match="supported official order endpoint|unsupported capability"):
        _build_input(payload)


def test_mock_domain_constraint_represented():
    result = run_kiwoom_mock_adapter_draft_mapping(_build_input())
    assert result.order_draft.metadata["mock_domain"] == "https://mockapi.kiwoom.com"


def test_krx_only_constraint_represented():
    result = run_kiwoom_mock_adapter_draft_mapping(_build_input())
    assert result.order_draft.metadata["mock_krx_only"] is True


def test_kiwoom_mock_order_draft_generation_success_path():
    result = run_kiwoom_mock_adapter_draft_mapping(_build_input())
    draft = result.order_draft
    assert draft.metadata["draft_status"] == "EVIDENCE_BACKED_DRAFT_ONLY"
    assert draft.documented_api_id == "KT10000"


def test_order_draft_remains_draft_only_non_executable():
    draft = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_draft
    assert draft.draft_only is True
    assert draft.non_executable is True


def test_order_request_draft_generation_success_path():
    request = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_request_draft
    assert request.metadata["draft_status"] == "REQUEST_SHAPE_ONLY"


def test_request_draft_has_endpoint_path_as_evidence_metadata_only():
    request = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_request_draft
    assert request.metadata["documented_endpoint_path"] == "/api/dostk/ordr"
    assert request.metadata["request_execution_enabled"] is False


def test_request_draft_has_no_credential_token_auth_client_network_fields():
    request = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_request_draft
    dumped = json.dumps(request.model_dump(mode="json")).lower()
    assert "\"authorization_header\"" not in dumped
    assert "\"access_token\"" not in dumped
    assert "\"app_key\"" not in dumped
    assert "\"secret_key\"" not in dumped
    assert "\"http_client\"" not in dumped
    assert "\"network_transport\"" not in dumped


def test_order_response_draft_generation_success_path():
    response = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_response_draft
    assert response.metadata["boundary_message"].startswith("Draft-only")


def test_response_draft_does_not_claim_real_kiwoom_or_mockapi_response():
    response = run_kiwoom_mock_adapter_draft_mapping(_build_input()).order_response_draft
    assert response.metadata["real_kiwoom_response"] is False
    assert response.metadata["mockapi_response_received"] is False


def test_execution_draft_generation_success_path():
    execution = run_kiwoom_mock_adapter_draft_mapping(_build_input()).execution_draft
    assert execution.metadata["draft_execution_only"] is True


def test_execution_draft_does_not_claim_real_execution():
    execution = run_kiwoom_mock_adapter_draft_mapping(_build_input()).execution_draft
    assert execution.metadata["real_execution"] is False


def test_account_snapshot_draft_generation_success_path():
    snapshot = run_kiwoom_mock_adapter_draft_mapping(_build_input()).account_snapshot_draft
    assert snapshot.metadata["draft_account_only"] is True


def test_account_snapshot_draft_has_no_real_account_number():
    snapshot = run_kiwoom_mock_adapter_draft_mapping(_build_input()).account_snapshot_draft
    assert snapshot.metadata["real_account_number_present"] is False


def test_position_snapshot_draft_generation_success_path():
    position = run_kiwoom_mock_adapter_draft_mapping(_build_input()).account_snapshot_draft.position_snapshots[0]
    assert position.metadata["draft_position_only"] is True


def test_safety_report_generation():
    report = run_kiwoom_mock_adapter_draft_mapping(_build_input()).safety_report
    assert report.blocked is False


def test_gap_report_generation():
    report = run_kiwoom_mock_adapter_draft_mapping(_build_input()).gap_report
    assert "KIWOOM_MOCK_DRAFT_GENERATED" in report.gap_categories


def test_audit_record_generation():
    record = run_kiwoom_mock_adapter_draft_mapping(_build_input()).audit_records[0]
    assert record.operator_context.startswith("TEST|KT10000|GAPS:")


@pytest.mark.parametrize(
    "side",
    [
        "KIWOOM_MOCK_BUY_DRAFT",
        "KIWOOM_MOCK_SELL_DRAFT",
        "KIWOOM_MOCK_CANCEL_DRAFT",
        "KIWOOM_MOCK_REPLACE_DRAFT",
        "KIWOOM_MOCK_CLOSE_DRAFT",
    ],
)
def test_draft_side_enum_accepted(side):
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["side"] = side
    result = run_kiwoom_mock_adapter_draft_mapping(_build_input(payload))
    assert result.order_draft.side.value == side


@pytest.mark.parametrize("side", ["BUY", "SELL", "CANCEL", "REPLACE", "CLOSE", "ORDER"])
def test_bare_buy_sell_cancel_replace_close_order_rejected(side):
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["side"] = side
    with pytest.raises(ValueError, match="bare order/action values"):
        _build_input(payload)


def test_real_order_intent_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["real_order_intent"] = "unsafe"
    with pytest.raises(ValueError, match="real order"):
        _build_input(payload)


def test_credential_token_auth_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["authorization_header"] = "Bearer X"
    with pytest.raises(ValueError, match="authorization|credentials|token"):
        _build_input(payload)


def test_oauth_token_request_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["oauth_token_request"] = True
    with pytest.raises(ValueError, match="oauth token"):
        _build_input(payload)


def test_api_mockapi_network_websocket_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["api_call"] = True
    with pytest.raises(ValueError, match="api call"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["mockapi_call"] = True
    with pytest.raises(ValueError, match="mockapi"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["network_call"] = True
    with pytest.raises(ValueError, match="network"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"]["websocket_connection"] = True
    with pytest.raises(ValueError, match="websocket"):
        _build_input(payload)


def test_real_account_mutation_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["account_snapshot_draft"]["metadata"]["real_account_mutation"] = True
    with pytest.raises(ValueError, match="real account mutation"):
        _build_input(payload)


def test_live_trading_live_prod_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["live_trading"] = True
    with pytest.raises(ValueError, match="live trading"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["mode"] = "LIVE"
    with pytest.raises(ValueError, match="live/prod"):
        _build_input(payload)


def test_broker_order_account_provider_api_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["broker_api_call"] = True
    with pytest.raises(ValueError, match="broker api"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["order_api_call"] = True
    with pytest.raises(ValueError, match="order api"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["account_api_call"] = True
    with pytest.raises(ValueError, match="account api"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["provider_api_call"] = True
    with pytest.raises(ValueError, match="provider api"):
        _build_input(payload)


def test_cloud_llm_local_llm_runtime_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["cloud_llm"] = "gemini"
    with pytest.raises(ValueError, match="cloud llm|gemini"):
        _build_input(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"]["local_llm_runtime"] = "ollama"
    with pytest.raises(ValueError, match="local llm runtime"):
        _build_input(payload)


def test_parquet_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["audit_records"][0]["source_path"] = "fixtures/kiwoom/adapter.parquet"
    with pytest.raises(ValueError, match="parquet"):
        _build_input(payload)


def test_load_kiwoom_mock_capability_matrix_local_json_only(tmp_path):
    capability_file = tmp_path / "capability.json"
    capability_file.write_text(json.dumps({"endpoints": []}), encoding="utf-8")
    loaded = load_kiwoom_mock_capability_matrix(capability_file)
    assert loaded["endpoints"] == []
