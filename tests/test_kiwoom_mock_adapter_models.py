import json

import pytest

from stock_risk_mcp.kiwoom_mock_adapter_fixture import load_kiwoom_mock_adapter_fixture
from stock_risk_mcp.kiwoom_mock_adapter_guard import validate_kiwoom_mock_adapter_metadata_safety
from stock_risk_mcp.kiwoom_mock_adapter_models import (
    KiwoomMockAdapterAuditRecord,
    KiwoomMockAdapterConfig,
    KiwoomMockAdapterGapReport,
    KiwoomMockAdapterInput,
    KiwoomMockAdapterSafetyReport,
    KiwoomMockCapabilityRef,
    KiwoomMockExecutionDraft,
    KiwoomMockOrderDraft,
    KiwoomMockOrderRequestDraft,
    KiwoomMockOrderResponseDraft,
    KiwoomMockPositionSnapshotDraft,
    KiwoomMockAccountSnapshotDraft,
    KiwoomMockDraftSide,
    KiwoomMockGapCategory,
)


def kiwoom_mock_adapter_fixture_payload():
    return {
        "schema_version": "v6.3-kiwoom-mock-adapter-input",
        "adapter_input_id": "kiwoom-mock-adapter-input-1",
        "adapter_config": {
            "config_id": "kiwoom-mock-adapter-config-1",
            "strategy_track": "DOMESTIC_KR",
            "market": "KRX",
            "broker_mock_adapter_id": "BROKER-MOCK-ADAPTER-INPUT-1",
            "evidence_pack_ref": "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-official-evidence-pack.md",
            "capability_matrix_ref": "docs/superpowers/specs/2026-06-18-kiwoom-rest-api-capability-matrix.json",
        },
        "capability_ref": {
            "capability_ref_id": "DOMESTIC_STOCK_ORDER_CREATE_MOCK",
            "evidence_endpoint_ref": "kt10000",
            "evidence_category": "국내주식 / 주문",
            "endpoint_path": "/api/dostk/ordr",
            "http_method": "POST",
            "mock_domain": "https://mockapi.kiwoom.com",
            "mock_krx_only": True,
            "documented_request_fields": [
                "dmst_stex_tp",
                "stk_cd",
                "ord_qty",
                "ord_uv",
                "trde_tp",
                "cond_uv",
            ],
            "documented_response_fields": ["ord_no", "dmst_stex_tp"],
            "supported_draft_sides": ["KIWOOM_MOCK_BUY_DRAFT", "KIWOOM_MOCK_SELL_DRAFT"],
            "supported_order_types": ["LIMIT"],
        },
        "order_draft": {
            "order_draft_id": "kiwoom-mock-order-draft-1",
            "source_broker_mock_order_intent_ref_id": "BROKER-MOCK-ORDER-INTENT-1",
            "source_paper_order_intent_ref_id": "HISTORICAL-PAPER-ORDER-INTENT-1",
            "source_signal_candidate_ref_id": "HISTORICAL-SIGNAL-CANDIDATE-1",
            "symbol": "005930",
            "market": "KRX",
            "market_profile": "DOMESTIC_EQUITY",
            "strategy_track": "DOMESTIC_KR",
            "side": "KIWOOM_MOCK_BUY_DRAFT",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": 70000,
            "documented_endpoint_path": "/api/dostk/ordr",
            "documented_api_id": "kt10000",
            "documented_required_fields": ["dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"],
            "source_manifest_ids": ["MANIFEST-1"],
            "source_audit_record_ids": ["AUDIT-1"],
            "provider_provenance_ids": ["PROVENANCE-1"],
            "metadata": {"mapping_stage": "draft_only"},
        },
        "order_request_draft": {
            "request_draft_id": "kiwoom-mock-order-request-draft-1",
            "order_draft_id": "kiwoom-mock-order-draft-1",
            "request_body_fields": {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": 10,
                "ord_uv": 70000,
                "trde_tp": "LIMIT",
                "cond_uv": "0",
            },
            "metadata": {"request_shape": "documented_only"},
        },
        "order_response_draft": {
            "response_draft_id": "kiwoom-mock-order-response-draft-1",
            "request_draft_id": "kiwoom-mock-order-request-draft-1",
            "documented_response_fields": ["ord_no", "dmst_stex_tp"],
            "metadata": {"response_shape": "documented_only"},
        },
        "execution_draft": {
            "execution_draft_id": "kiwoom-mock-execution-draft-1",
            "order_draft_id": "kiwoom-mock-order-draft-1",
            "request_draft_id": "kiwoom-mock-order-request-draft-1",
            "response_draft_id": "kiwoom-mock-order-response-draft-1",
            "symbol": "005930",
            "side": "KIWOOM_MOCK_BUY_DRAFT",
            "documented_status": "DRAFT_ONLY",
            "metadata": {"execution_shape": "documented_only"},
        },
        "account_snapshot_draft": {
            "account_snapshot_draft_id": "kiwoom-mock-account-snapshot-draft-1",
            "base_currency": "KRW",
            "position_snapshots": [
                {
                    "position_snapshot_draft_id": "kiwoom-mock-position-snapshot-draft-1",
                    "symbol": "005930",
                    "market": "KRX",
                    "quantity": 0,
                    "average_price": 0,
                    "mark_price": 0,
                    "exposure_value": 0,
                    "metadata": {"position_shape": "draft_only"},
                }
            ],
            "metadata": {"account_shape": "draft_only"},
        },
        "safety_report": {
            "safety_report_id": "kiwoom-mock-safety-report-1",
            "blocked": False,
            "findings": [],
        },
        "gap_report": {
            "gap_report_id": "kiwoom-mock-gap-report-1",
            "adapter_input_id": "kiwoom-mock-adapter-input-1",
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
                "audit_record_id": "kiwoom-mock-audit-record-1",
                "adapter_input_id": "kiwoom-mock-adapter-input-1",
                "created_at": "2026-06-22T18:00:00+09:00",
                "operator_context": "TEST",
                "source_path": "fixtures/kiwoom/kiwoom_mock_adapter_fixture.json",
                "source_manifest_ids": ["MANIFEST-1"],
                "source_audit_record_ids": ["AUDIT-1"],
                "provider_provenance_ids": ["PROVENANCE-1"],
            }
        ],
    }


def test_valid_config_construction():
    adapter_input = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload())
    assert isinstance(adapter_input.adapter_config, KiwoomMockAdapterConfig)
    assert adapter_input.adapter_config.disabled_by_default is True


def test_required_safety_flags():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["adapter_config"]["no_network_call"] = False
    with pytest.raises(ValueError, match="no_network_call"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_capability_ref_construction():
    adapter_input = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload())
    assert isinstance(adapter_input.capability_ref, KiwoomMockCapabilityRef)
    assert adapter_input.capability_ref.evidence_endpoint_ref == "KT10000"


def test_adapter_input_construction():
    adapter_input = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload())
    assert isinstance(adapter_input, KiwoomMockAdapterInput)
    assert adapter_input.adapter_input_id == "KIWOOM-MOCK-ADAPTER-INPUT-1"


def test_order_draft_construction():
    adapter_input = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload())
    assert isinstance(adapter_input.order_draft, KiwoomMockOrderDraft)
    assert adapter_input.order_draft.side == KiwoomMockDraftSide.KIWOOM_MOCK_BUY_DRAFT


def test_order_draft_is_draft_only_non_executable():
    draft = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).order_draft
    assert draft.draft_only is True
    assert draft.non_executable is True


def test_order_request_draft_construction():
    request = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).order_request_draft
    assert isinstance(request, KiwoomMockOrderRequestDraft)


def test_order_request_draft_has_no_credential_token_auth_network_client_fields():
    request = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).order_request_draft
    dumped = json.dumps(request.model_dump(mode="json")).lower()
    assert "\"authorization_header\"" not in dumped
    assert "\"access_token\"" not in dumped
    assert "\"app_key\"" not in dumped
    assert "\"secret_key\"" not in dumped
    assert "\"http_client\"" not in dumped
    assert "\"transport_client\"" not in dumped


def test_order_response_draft_construction():
    response = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).order_response_draft
    assert isinstance(response, KiwoomMockOrderResponseDraft)


def test_execution_draft_construction():
    execution = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).execution_draft
    assert isinstance(execution, KiwoomMockExecutionDraft)


def test_account_snapshot_draft_construction():
    snapshot = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).account_snapshot_draft
    assert isinstance(snapshot, KiwoomMockAccountSnapshotDraft)


def test_position_snapshot_draft_construction():
    snapshot = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).account_snapshot_draft
    assert isinstance(snapshot.position_snapshots[0], KiwoomMockPositionSnapshotDraft)


def test_safety_report_construction():
    report = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).safety_report
    assert isinstance(report, KiwoomMockAdapterSafetyReport)
    assert report.no_api_call is True


def test_gap_report_construction():
    report = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).gap_report
    assert isinstance(report, KiwoomMockAdapterGapReport)
    assert report.gap_status == "NO_GAPS"


def test_audit_record_construction():
    record = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).audit_records[0]
    assert isinstance(record, KiwoomMockAdapterAuditRecord)


def test_local_fixture_loader_success(tmp_path):
    fixture_path = tmp_path / "kiwoom_mock_adapter_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_mock_adapter_fixture_payload()), encoding="utf-8")
    loaded = load_kiwoom_mock_adapter_fixture(fixture_path)
    assert loaded.adapter_input_id == "KIWOOM-MOCK-ADAPTER-INPUT-1"


def test_local_fixture_loader_failure_includes_source_path(tmp_path):
    fixture_path = tmp_path / "broken.json"
    fixture_path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match=str(fixture_path)):
        load_kiwoom_mock_adapter_fixture(fixture_path)


def test_evidence_endpoint_ref_required():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["capability_ref"]["evidence_endpoint_ref"] = ""
    with pytest.raises(ValueError, match="evidence_endpoint_ref"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_mock_domain_krx_only_constraint_represented():
    capability = KiwoomMockAdapterInput.model_validate(kiwoom_mock_adapter_fixture_payload()).capability_ref
    assert capability.mock_domain == "https://mockapi.kiwoom.com"
    assert capability.mock_krx_only is True


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
def test_draft_only_side_values_accepted(side):
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["side"] = side
    adapter_input = KiwoomMockAdapterInput.model_validate(payload)
    assert adapter_input.order_draft.side.value == side


@pytest.mark.parametrize("side", ["BUY", "SELL", "CANCEL", "REPLACE", "CLOSE", "ORDER"])
def test_bare_buy_sell_cancel_replace_close_order_rejected(side):
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["side"] = side
    with pytest.raises(ValueError, match="bare order/action values"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_real_order_intent_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["real_order_intent"] = "unsafe"
    with pytest.raises(ValueError, match="real order"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_credential_token_auth_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"authorization_header": "Bearer X"}
    with pytest.raises(ValueError, match="authorization|credentials|token"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_oauth_token_request_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"oauth_token_request": True}
    with pytest.raises(ValueError, match="oauth token"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_api_mockapi_network_websocket_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"api_call": True}
    with pytest.raises(ValueError, match="api call"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"mockapi_call": True}
    with pytest.raises(ValueError, match="mockapi"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"network_call": True}
    with pytest.raises(ValueError, match="network"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_request_draft"]["metadata"] = {"websocket_connection": True}
    with pytest.raises(ValueError, match="websocket"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_real_account_mutation_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["account_snapshot_draft"]["metadata"]["real_account_mutation"] = True
    with pytest.raises(ValueError, match="real account mutation"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_live_trading_live_prod_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["live_trading"] = True
    with pytest.raises(ValueError, match="live trading"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_draft"]["metadata"]["mode"] = "LIVE"
    with pytest.raises(ValueError, match="live/prod"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_broker_order_account_provider_api_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"broker_api_call": True}
    with pytest.raises(ValueError, match="broker api"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"order_api_call": True}
    with pytest.raises(ValueError, match="order api"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"account_api_call": True}
    with pytest.raises(ValueError, match="account api"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"provider_api_call": True}
    with pytest.raises(ValueError, match="provider api"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_cloud_llm_local_llm_runtime_marker_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"cloud_llm": "gemini"}
    with pytest.raises(ValueError, match="cloud llm|gemini"):
        KiwoomMockAdapterInput.model_validate(payload)
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["order_response_draft"]["metadata"] = {"local_llm_runtime": "ollama"}
    with pytest.raises(ValueError, match="local llm runtime"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_parquet_rejected():
    payload = kiwoom_mock_adapter_fixture_payload()
    payload["audit_records"][0]["source_path"] = "fixtures/kiwoom/adapter.parquet"
    with pytest.raises(ValueError, match="parquet"):
        KiwoomMockAdapterInput.model_validate(payload)


def test_required_gap_categories_exist():
    expected = {
        "KIWOOM_MOCK_DRAFT_GENERATED",
        "KIWOOM_MOCK_EVIDENCE_BACKED",
        "KIWOOM_MOCK_DRAFT_ONLY",
        "KIWOOM_MOCK_LOCAL_ONLY",
        "KIWOOM_MOCK_OFFLINE_ONLY",
        "KIWOOM_MOCK_DISABLED_BY_DEFAULT",
        "KIWOOM_MOCK_EXPLICIT_OPT_IN_REQUIRED",
        "KIWOOM_MOCK_NON_EXECUTABLE",
        "KIWOOM_MOCK_MISSING_INPUT",
        "KIWOOM_MOCK_MISSING_CAPABILITY_REF",
        "KIWOOM_MOCK_MISSING_BROKER_MOCK_ORDER_INTENT_REF",
        "KIWOOM_MOCK_MISSING_EVIDENCE_ENDPOINT_REF",
        "KIWOOM_MOCK_UNSUPPORTED_CAPABILITY",
        "KIWOOM_MOCK_UNSUPPORTED_ORDER_SIDE",
        "KIWOOM_MOCK_UNSUPPORTED_ORDER_TYPE",
        "KIWOOM_MOCK_MOCK_DOMAIN_REQUIRED",
        "KIWOOM_MOCK_KRX_ONLY_CONSTRAINT",
        "KIWOOM_MOCK_CREDENTIALS_NOT_ALLOWED",
        "KIWOOM_MOCK_OAUTH_TOKEN_REQUEST_NOT_ALLOWED",
        "KIWOOM_MOCK_API_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_MOCKAPI_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_NETWORK_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_WEBSOCKET_NOT_ALLOWED",
        "KIWOOM_MOCK_REAL_ORDER_NOT_ALLOWED",
        "KIWOOM_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED",
        "KIWOOM_MOCK_LIVE_TRADING_NOT_ALLOWED",
        "KIWOOM_MOCK_LIVE_PROD_NOT_ALLOWED",
        "KIWOOM_MOCK_BROKER_API_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_ORDER_API_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_PROVIDER_API_CALL_NOT_ALLOWED",
        "KIWOOM_MOCK_CLOUD_LLM_NOT_ALLOWED",
        "KIWOOM_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED",
        "KIWOOM_MOCK_PARQUET_NOT_ALLOWED",
    }
    actual = {item.value for item in KiwoomMockGapCategory}
    assert expected.issubset(actual)


def test_validate_kiwoom_mock_adapter_metadata_safety_rejects_external_markers():
    with pytest.raises(ValueError, match="oauth token|credentials|api call|websocket|parquet"):
        validate_kiwoom_mock_adapter_metadata_safety(
            {"oauth_token_request": True, "api_call": True, "websocket_connection": True, "parquet_path": "x.parquet"},
            context="test",
        )
