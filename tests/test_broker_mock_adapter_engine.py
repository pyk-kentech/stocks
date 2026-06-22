import json

import pytest

from stock_risk_mcp.broker_mock_adapter_engine import (
    load_broker_mock_capability_matrix,
    run_broker_mock_adapter_boundary,
)
from stock_risk_mcp.broker_mock_adapter_models import BrokerMockAdapterInput
from tests.test_broker_mock_adapter_models import broker_mock_adapter_fixture_payload


def _build_input(payload=None):
    return BrokerMockAdapterInput.model_validate(payload or broker_mock_adapter_fixture_payload())


def test_capability_validation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.capability.capability_id == "BROKER-MOCK-CAPABILITY-1"
    assert result.capability.supports_deterministic_replay_mode is True


def test_unsupported_capability_produces_gap():
    payload = broker_mock_adapter_fixture_payload()
    payload["capability"]["supports_mock_order_submission"] = True
    result = run_broker_mock_adapter_boundary(_build_input(payload))
    assert "BROKER_MOCK_UNSUPPORTED_CAPABILITY" in result.gap_report.gap_categories


def test_capability_requiring_real_live_prod_execution_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["capability"]["supports_async_callback_simulation"] = True
    result = run_broker_mock_adapter_boundary(_build_input(payload))
    assert "BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED" in result.gap_report.gap_categories


def test_mock_order_intent_boundary_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_order_intent.metadata["boundary_status"] == "LOCAL_MOCK_ONLY"


def test_mock_order_intent_remains_mock_only_paper_only_disabled_by_default():
    result = run_broker_mock_adapter_boundary(_build_input())
    intent = result.broker_mock_order_intent
    assert intent.mock_only is True
    assert intent.paper_only is True
    assert intent.disabled_by_default is True


def test_mock_order_request_boundary_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    request = result.broker_mock_order_request
    assert request.request_metadata["boundary_status"] == "REQUEST_SHAPE_ONLY"


def test_mock_order_request_has_no_endpoint_token_account_transport_fields():
    result = run_broker_mock_adapter_boundary(_build_input())
    metadata_dump = json.dumps(result.broker_mock_order_request.request_metadata).lower()
    assert "endpoint" not in metadata_dump
    assert "token" not in metadata_dump
    assert "account" not in metadata_dump
    assert "transport client" not in metadata_dump


def test_mock_order_response_boundary_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_order_response.response_metadata["no_execution"] is True


def test_mock_execution_report_boundary_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_execution_report.execution_metadata["mock_request_ref"] == "BROKER-MOCK-ORDER-REQUEST-1"


def test_mock_execution_report_does_not_claim_real_execution():
    result = run_broker_mock_adapter_boundary(_build_input())
    metadata = result.broker_mock_execution_report.execution_metadata
    assert metadata["real_execution"] is False
    assert metadata["exchange_confirmation"] is False
    assert metadata["broker_confirmation"] is False


def test_mock_account_snapshot_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_account_snapshot.metadata["boundary_status"] == "ACCOUNT_SNAPSHOT_ONLY"


def test_mock_account_snapshot_has_no_real_account_number():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_account_snapshot.metadata["real_account_number_present"] is False


def test_mock_position_snapshot_generation_success_path():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.broker_mock_account_snapshot.position_snapshots[0].metadata["boundary_status"] == "POSITION_SNAPSHOT_ONLY"


def test_kiwoom_boundary_remains_future_only_non_executable():
    result = run_broker_mock_adapter_boundary(_build_input())
    boundary = result.kiwoom_mock_adapter_boundary
    assert boundary.future_only is True
    assert boundary.implementation_present is False


def test_ls_boundary_remains_future_only_non_executable():
    result = run_broker_mock_adapter_boundary(_build_input())
    boundary = result.ls_mock_adapter_boundary
    assert boundary.future_only is True
    assert boundary.implementation_present is False


def test_safety_report_generation():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.safety_report.blocked is False


def test_gap_report_generation():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert "BROKER_MOCK_BOUNDARY_GENERATED" in result.gap_report.gap_categories


def test_audit_record_generation():
    result = run_broker_mock_adapter_boundary(_build_input())
    assert result.audit_records[0].audit_record_id == "BROKER-MOCK-AUDIT-RECORD-1"


def test_missing_paper_order_intent_ref_gap():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["source_paper_order_intent_ref_id"] = ""
    with pytest.raises(ValueError, match="source_paper_order_intent_ref_id must not be blank"):
        _build_input(payload)


def test_missing_capability_gap():
    payload = broker_mock_adapter_fixture_payload()
    payload["capability"]["supported_order_sides"] = []
    result = run_broker_mock_adapter_boundary(_build_input(payload))
    assert "BROKER_MOCK_MISSING_CAPABILITY" in result.gap_report.gap_categories


def test_unsupported_order_side_gap():
    payload = broker_mock_adapter_fixture_payload()
    payload["capability"]["supported_order_sides"] = ["MOCK_SELL"]
    result = run_broker_mock_adapter_boundary(_build_input(payload))
    assert "BROKER_MOCK_UNSUPPORTED_ORDER_SIDE" in result.gap_report.gap_categories


@pytest.mark.parametrize("side", ["BUY", "SELL", "CANCEL", "REPLACE", "CLOSE", "ORDER"])
def test_bare_order_values_rejected(side):
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["side"] = side
    with pytest.raises(ValueError, match="bare order/action values"):
        _build_input(payload)


def test_real_order_intent_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["metadata"]["real_order_intent"] = "unsafe"
    with pytest.raises(ValueError, match="real order"):
        _build_input(payload)


def test_real_account_mutation_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_account_snapshot"]["metadata"]["real_account_mutation"] = True
    with pytest.raises(ValueError, match="real account mutation"):
        _build_input(payload)


def test_credential_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_request"]["request_metadata"]["token"] = "unsafe"
    with pytest.raises(ValueError, match="credentials"):
        _build_input(payload)


def test_api_endpoint_network_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_request"]["request_metadata"]["api_endpoint"] = "https://example.test"
    with pytest.raises(ValueError, match="api endpoint"):
        _build_input(payload)


def test_kiwoom_api_call_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["kiwoom_mock_adapter_boundary"]["metadata"]["kiwoom_api_call"] = True
    with pytest.raises(ValueError, match="kiwoom api"):
        _build_input(payload)


def test_ls_api_call_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["ls_mock_adapter_boundary"]["metadata"]["ls_api_call"] = True
    with pytest.raises(ValueError, match="ls api"):
        _build_input(payload)


@pytest.mark.parametrize("field_name", ["broker_api_call", "order_api_call", "account_api_call", "provider_api_call"])
def test_broker_order_account_provider_api_markers_rejected(field_name):
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_response"]["response_metadata"][field_name] = True
    with pytest.raises(ValueError, match="broker api|order api|account api|provider api"):
        _build_input(payload)


@pytest.mark.parametrize("value", [{"live_trading": True}, {"mode": "LIVE"}, {"mode": "PROD"}])
def test_live_trading_live_prod_marker_rejected(value):
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["metadata"].update(value)
    with pytest.raises(ValueError, match="live trading|live/prod"):
        _build_input(payload)


def test_cloud_llm_local_llm_runtime_marker_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_response"]["response_metadata"]["cloud_llm"] = "gemini"
    with pytest.raises(ValueError, match="cloud llm"):
        _build_input(payload)
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_response"]["response_metadata"]["local_llm_runtime"] = "ollama"
    with pytest.raises(ValueError, match="local llm runtime"):
        _build_input(payload)


def test_parquet_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["audit_records"][0]["source_path"] = "fixtures/historical/broker_mock_adapter_fixture.parquet"
    with pytest.raises(ValueError, match="parquet"):
        _build_input(payload)


def test_load_broker_mock_capability_matrix_local_json_only(tmp_path):
    capability_file = tmp_path / "capability.json"
    capability_file.write_text(json.dumps({"capabilities": []}), encoding="utf-8")
    loaded = load_broker_mock_capability_matrix(capability_file)
    assert loaded["capabilities"] == []
