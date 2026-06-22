import json

import pytest

from stock_risk_mcp.broker_mock_adapter_fixture import load_broker_mock_adapter_fixture
from stock_risk_mcp.broker_mock_adapter_guard import validate_broker_mock_adapter_metadata_safety
from stock_risk_mcp.broker_mock_adapter_models import (
    BrokerMockAccountSnapshot,
    BrokerMockAdapterAuditRecord,
    BrokerMockAdapterConfig,
    BrokerMockAdapterGapReport,
    BrokerMockAdapterInput,
    BrokerMockAdapterSafetyReport,
    BrokerMockCapability,
    BrokerMockExecutionReport,
    BrokerMockGapCategory,
    BrokerMockOrderIntent,
    BrokerMockOrderRequest,
    BrokerMockOrderResponse,
    BrokerMockOrderSide,
    BrokerMockPositionSnapshot,
    KiwoomMockAdapterBoundary,
    LSMockAdapterBoundary,
)


def broker_mock_adapter_fixture_payload():
    return {
        "schema_version": "v6.2-broker-mock-adapter-input",
        "adapter_input_id": "broker-mock-adapter-input-1",
        "adapter_config": {
            "config_id": "broker-mock-adapter-config-1",
            "strategy_track": "DOMESTIC_KR",
            "mock_adapter_family": "GENERIC_BROKER_MOCK",
        },
        "capability": {
            "capability_id": "broker-mock-capability-1",
            "supported_markets": ["KRX"],
            "supported_order_types": ["LIMIT"],
            "supported_order_sides": ["MOCK_BUY", "MOCK_SELL", "MOCK_CANCEL", "MOCK_REPLACE", "MOCK_CLOSE"],
            "supports_mock_order_submission": False,
            "supports_mock_cancellation": False,
            "supports_mock_status_polling": False,
            "supports_mock_account_snapshot": False,
            "supports_mock_position_snapshot": False,
            "supports_deterministic_replay_mode": True,
            "supports_async_callback_simulation": False,
        },
        "broker_mock_order_intent": {
            "mock_order_intent_id": "broker-mock-order-intent-1",
            "source_paper_order_intent_ref_id": "historical-paper-order-intent-1",
            "source_paper_decision_ref_id": "historical-paper-decision-1",
            "source_signal_candidate_ref_id": "historical-signal-candidate-1",
            "symbol": "005930",
            "market": "KRX",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": "DOMESTIC_EQUITY",
            "side": "MOCK_BUY",
            "mock_order_type": "LIMIT",
            "requested_quantity": 10,
            "session_timestamp": "2026-06-22T09:10:00+09:00",
            "mock_adapter_target_id": "generic-broker-mock",
            "source_manifest_ids": ["MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
            "metadata": {"simulation_stage": "boundary_only"},
        },
        "broker_mock_order_request": {
            "mock_order_request_id": "broker-mock-order-request-1",
            "mock_order_intent_id": "broker-mock-order-intent-1",
            "request_created_at": "2026-06-22T09:10:05+09:00",
            "request_metadata": {"request_mode": "mock_boundary_only"},
        },
        "broker_mock_order_response": {
            "mock_order_response_id": "broker-mock-order-response-1",
            "mock_order_request_id": "broker-mock-order-request-1",
            "mock_status": "MOCK_ACCEPTED",
            "response_timestamp": "2026-06-22T09:10:06+09:00",
            "response_metadata": {"response_mode": "mock_boundary_only"},
        },
        "broker_mock_execution_report": {
            "execution_report_id": "broker-mock-execution-report-1",
            "mock_order_intent_id": "broker-mock-order-intent-1",
            "mock_order_request_id": "broker-mock-order-request-1",
            "mock_order_response_id": "broker-mock-order-response-1",
            "symbol": "005930",
            "side": "MOCK_BUY",
            "mock_status": "MOCK_ACCEPTED",
            "mock_filled_quantity": 0,
            "mock_average_fill_price": 0,
            "mock_execution_timestamp": "2026-06-22T09:10:06+09:00",
            "execution_metadata": {"execution_mode": "mock_boundary_only"},
        },
        "broker_mock_account_snapshot": {
            "account_snapshot_id": "broker-mock-account-snapshot-1",
            "mock_adapter_id": "generic-broker-mock",
            "snapshot_timestamp": "2026-06-22T09:10:07+09:00",
            "base_currency": "KRW",
            "reported_mock_cash": 1000000,
            "reported_mock_buying_power": 1000000,
            "reported_mock_equity": 1000000,
            "position_snapshots": [
                {
                    "position_snapshot_id": "broker-mock-position-snapshot-1",
                    "symbol": "005930",
                    "market": "KRX",
                    "quantity": 0,
                    "average_price": 0,
                    "mark_price": 0,
                    "exposure_value": 0,
                    "metadata": {"position_mode": "mock_boundary_only"},
                }
            ],
            "metadata": {"account_mode": "mock_boundary_only"},
        },
        "kiwoom_mock_adapter_boundary": {
            "boundary_id": "kiwoom-mock-adapter-boundary-1",
            "future_only": True,
            "implementation_present": False,
            "executable_transport_present": False,
            "metadata": {"boundary_family": "future_boundary_only"},
        },
        "ls_mock_adapter_boundary": {
            "boundary_id": "ls-mock-adapter-boundary-1",
            "future_only": True,
            "implementation_present": False,
            "executable_transport_present": False,
            "metadata": {"boundary_family": "future_boundary_only"},
        },
        "safety_report": {
            "safety_report_id": "broker-mock-safety-report-1",
            "blocked": False,
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "broker-mock-gap-report-1",
            "adapter_input_id": "broker-mock-adapter-input-1",
            "gap_status": "NO_GAPS",
            "gap_categories": [],
            "blocking_gap_count": 0,
            "report_only_gap_count": 0,
            "gaps": [],
            "source_manifest_ids": ["MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
        },
        "audit_records": [
            {
                "audit_record_id": "broker-mock-audit-record-1",
                "adapter_input_id": "broker-mock-adapter-input-1",
                "created_at": "2026-06-22T09:11:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/historical/broker_mock_adapter_fixture.json",
                "source_manifest_ids": ["MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
    }


def test_valid_config_construction():
    adapter_input = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload())
    assert isinstance(adapter_input.adapter_config, BrokerMockAdapterConfig)
    assert adapter_input.adapter_config.enabled is False


def test_required_safety_flags():
    payload = broker_mock_adapter_fixture_payload()
    payload["adapter_config"]["no_network_call"] = False
    with pytest.raises(ValueError, match="no_network_call"):
        BrokerMockAdapterInput.model_validate(payload)


def test_broker_mock_capability_construction():
    adapter_input = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload())
    assert isinstance(adapter_input.capability, BrokerMockCapability)
    assert adapter_input.capability.supported_order_sides[0] == BrokerMockOrderSide.MOCK_BUY


def test_broker_mock_adapter_input_construction():
    adapter_input = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload())
    assert isinstance(adapter_input, BrokerMockAdapterInput)
    assert adapter_input.adapter_input_id == "BROKER-MOCK-ADAPTER-INPUT-1"


def test_broker_mock_order_intent_construction():
    adapter_input = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload())
    intent = adapter_input.broker_mock_order_intent
    assert isinstance(intent, BrokerMockOrderIntent)
    assert intent.side == BrokerMockOrderSide.MOCK_BUY


def test_broker_mock_order_intent_is_mock_only_paper_only_disabled_by_default():
    intent = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_order_intent
    assert intent.mock_only is True
    assert intent.paper_only is True
    assert intent.disabled_by_default is True
    assert intent.non_executable_by_default is True


def test_broker_mock_order_intent_does_not_expose_real_order_intent():
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["metadata"]["real_order_intent"] = "unsafe"
    with pytest.raises(ValueError, match="real order"):
        BrokerMockAdapterInput.model_validate(payload)


def test_broker_mock_order_request_construction():
    request = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_order_request
    assert isinstance(request, BrokerMockOrderRequest)


def test_broker_mock_order_response_construction():
    response = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_order_response
    assert isinstance(response, BrokerMockOrderResponse)


def test_broker_mock_execution_report_construction():
    report = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_execution_report
    assert isinstance(report, BrokerMockExecutionReport)


def test_broker_mock_account_snapshot_construction():
    snapshot = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_account_snapshot
    assert isinstance(snapshot, BrokerMockAccountSnapshot)


def test_broker_mock_position_snapshot_construction():
    snapshot = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).broker_mock_account_snapshot
    assert isinstance(snapshot.position_snapshots[0], BrokerMockPositionSnapshot)


def test_kiwoom_mock_boundary_is_future_only_and_non_executable():
    boundary = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).kiwoom_mock_adapter_boundary
    assert isinstance(boundary, KiwoomMockAdapterBoundary)
    assert boundary.future_only is True
    assert boundary.implementation_present is False


def test_ls_mock_boundary_is_future_only_and_non_executable():
    boundary = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).ls_mock_adapter_boundary
    assert isinstance(boundary, LSMockAdapterBoundary)
    assert boundary.future_only is True
    assert boundary.implementation_present is False


def test_safety_report_construction():
    report = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).safety_report
    assert isinstance(report, BrokerMockAdapterSafetyReport)
    assert report.no_broker_api_call is True


def test_gap_report_construction():
    report = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).gap_report
    assert isinstance(report, BrokerMockAdapterGapReport)
    assert report.gap_status == "NO_GAPS"


def test_audit_record_construction():
    record = BrokerMockAdapterInput.model_validate(broker_mock_adapter_fixture_payload()).audit_records[0]
    assert isinstance(record, BrokerMockAdapterAuditRecord)
    assert record.source_path.endswith(".json")


def test_local_fixture_loader_success(tmp_path):
    fixture_file = tmp_path / "broker_mock_adapter_fixture.json"
    fixture_file.write_text(json.dumps(broker_mock_adapter_fixture_payload()), encoding="utf-8")
    loaded = load_broker_mock_adapter_fixture(fixture_file)
    assert isinstance(loaded, BrokerMockAdapterInput)


def test_local_fixture_loader_failure_includes_source_path(tmp_path):
    fixture_file = tmp_path / "broker_mock_adapter_fixture.txt"
    fixture_file.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=str(fixture_file)):
        load_broker_mock_adapter_fixture(fixture_file)


@pytest.mark.parametrize("side", ["MOCK_BUY", "MOCK_SELL", "MOCK_CANCEL", "MOCK_REPLACE", "MOCK_CLOSE"])
def test_mock_only_side_values_accepted(side):
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["side"] = side
    adapter_input = BrokerMockAdapterInput.model_validate(payload)
    assert adapter_input.broker_mock_order_intent.side.value == side


@pytest.mark.parametrize("side", ["BUY", "SELL", "CANCEL", "REPLACE", "CLOSE", "ORDER"])
def test_bare_order_action_values_rejected(side):
    payload = broker_mock_adapter_fixture_payload()
    payload["broker_mock_order_intent"]["side"] = side
    with pytest.raises(ValueError, match="bare order/action values"):
        BrokerMockAdapterInput.model_validate(payload)


def test_real_account_mutation_marker_rejected():
    with pytest.raises(ValueError, match="real account mutation"):
        validate_broker_mock_adapter_metadata_safety({"real_account_mutation": True}, context="test")


def test_production_broker_marker_rejected():
    with pytest.raises(ValueError, match="production broker"):
        validate_broker_mock_adapter_metadata_safety({"production_broker": "unsafe"}, context="test")


@pytest.mark.parametrize("value", [{"live_trading": True}, {"mode": "LIVE"}, {"mode": "PROD"}])
def test_live_trading_live_prod_marker_rejected(value):
    with pytest.raises(ValueError, match="live trading|live/prod"):
        validate_broker_mock_adapter_metadata_safety(value, context="test")


def test_api_endpoint_network_marker_rejected():
    with pytest.raises(ValueError, match="api endpoint|network"):
        validate_broker_mock_adapter_metadata_safety({"api_endpoint": "https://example.test"}, context="test")


def test_kiwoom_api_call_marker_rejected():
    with pytest.raises(ValueError, match="kiwoom api"):
        validate_broker_mock_adapter_metadata_safety({"kiwoom_api_call": True}, context="test")


def test_ls_api_call_marker_rejected():
    with pytest.raises(ValueError, match="ls api"):
        validate_broker_mock_adapter_metadata_safety({"ls_api_call": True}, context="test")


@pytest.mark.parametrize("key", ["broker_api_call", "order_api_call", "account_api_call", "provider_api_call"])
def test_broker_order_account_provider_api_markers_rejected(key):
    with pytest.raises(ValueError, match="broker api|order api|account api|provider api"):
        validate_broker_mock_adapter_metadata_safety({key: True}, context="test")


@pytest.mark.parametrize("key", ["credentials", "token", "secret"])
def test_credentials_tokens_secrets_rejected(key):
    with pytest.raises(ValueError, match="credentials"):
        validate_broker_mock_adapter_metadata_safety({key: "unsafe"}, context="test")


def test_cloud_llm_local_llm_runtime_markers_rejected():
    with pytest.raises(ValueError, match="cloud llm"):
        validate_broker_mock_adapter_metadata_safety({"cloud_llm": "gemini"}, context="test")
    with pytest.raises(ValueError, match="local llm runtime"):
        validate_broker_mock_adapter_metadata_safety({"local_llm_runtime": "ollama"}, context="test")


def test_parquet_rejected():
    payload = broker_mock_adapter_fixture_payload()
    payload["audit_records"][0]["source_path"] = "fixtures/historical/broker_mock_adapter_fixture.parquet"
    with pytest.raises(ValueError, match="parquet"):
        BrokerMockAdapterInput.model_validate(payload)


def test_required_gap_categories_exist():
    expected = {
        "BROKER_MOCK_BOUNDARY_GENERATED",
        "BROKER_MOCK_LOCAL_ONLY",
        "BROKER_MOCK_OFFLINE_ONLY",
        "BROKER_MOCK_MOCK_ONLY",
        "BROKER_MOCK_PAPER_ONLY",
        "BROKER_MOCK_DISABLED_BY_DEFAULT",
        "BROKER_MOCK_EXPLICIT_OPT_IN_REQUIRED",
        "BROKER_MOCK_NON_EXECUTABLE_BY_DEFAULT",
        "BROKER_MOCK_MISSING_INPUT",
        "BROKER_MOCK_MISSING_PAPER_ORDER_INTENT_REF",
        "BROKER_MOCK_MISSING_CAPABILITY",
        "BROKER_MOCK_UNSUPPORTED_CAPABILITY",
        "BROKER_MOCK_UNSUPPORTED_ORDER_TYPE",
        "BROKER_MOCK_UNSUPPORTED_ORDER_SIDE",
        "BROKER_MOCK_REAL_ORDER_NOT_ALLOWED",
        "BROKER_MOCK_REAL_ORDER_INTENT_NOT_ALLOWED",
        "BROKER_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED",
        "BROKER_MOCK_LIVE_TRADING_NOT_ALLOWED",
        "BROKER_MOCK_LIVE_PROD_NOT_ALLOWED",
        "BROKER_MOCK_PRODUCTION_BROKER_NOT_ALLOWED",
        "BROKER_MOCK_CREDENTIALS_NOT_ALLOWED",
        "BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED",
        "BROKER_MOCK_KIWOOM_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_LS_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_BROKER_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_ORDER_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_PROVIDER_API_CALL_NOT_ALLOWED",
        "BROKER_MOCK_CLOUD_LLM_NOT_ALLOWED",
        "BROKER_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "BROKER_MOCK_PARQUET_NOT_ALLOWED",
    }
    assert expected == {item.value for item in BrokerMockGapCategory}
