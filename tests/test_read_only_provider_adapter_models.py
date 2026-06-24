import json

import pytest

from stock_risk_mcp.read_only_provider_adapter_fixture import load_read_only_provider_adapter_fixture
from stock_risk_mcp.read_only_provider_adapter_guard import (
    validate_read_only_provider_adapter_metadata_safety,
)
from stock_risk_mcp.read_only_provider_adapter_models import (
    ReadOnlyProvider,
    ProviderRole,
    ReadOnlyProviderAdapterInput,
)


def read_only_provider_adapter_payload(**overrides):
    payload = {
        "adapter_id": "read-only-provider-boundary-1",
        "current_provider": "KIWOOM_REST",
        "future_provider": "LS_OPEN_API",
        "provider_definitions": [
            {
                "provider": "KIWOOM_REST",
                "role": "CURRENT_PRIMARY",
                "markets_supported": ["KRX_EQUITY", "KOSDAQ_EQUITY"],
                "implemented": True,
                "placeholder_only": False,
                "future_api_evidence_required": False,
                "evidence_ref": "docs/evidence/kiwoom_rest_readonly.md",
                "notes": "current domestic read-only primary provider",
            },
            {
                "provider": "LS_OPEN_API",
                "role": "FUTURE_MIGRATION_TARGET",
                "markets_supported": ["KRX_EQUITY", "GLOBAL_FUTURES"],
                "implemented": False,
                "placeholder_only": True,
                "future_api_evidence_required": True,
                "notes": "future migration target pending exact LS evidence",
            },
            {
                "provider": "LOCAL_FIXTURE",
                "role": "FIXTURE_ONLY",
                "markets_supported": ["TEST_ONLY"],
                "implemented": True,
                "placeholder_only": False,
                "future_api_evidence_required": False,
                "evidence_ref": "docs/evidence/local_fixture_boundary.md",
                "notes": "local fixture development provider",
            },
        ],
        "request_envelope_boundary": {
            "authorization_template": "Bearer <TOKEN_REF_ONLY>",
        },
        "kiwoom_rest_evidence_entries": [
            {"api_id": "AU10001", "title": "접근토큰 발급", "category": "OAUTH", "maps_to": ["TOKEN_BOUNDARY"], "blocked_in_readonly": True},
            {"api_id": "AU10002", "title": "접근토큰폐기", "category": "OAUTH", "maps_to": ["TOKEN_BOUNDARY"], "blocked_in_readonly": True},
            {"api_id": "KA10004", "title": "주식호가요청", "category": "QUOTE_ORDERBOOK", "maps_to": ["CANONICAL_QUOTE"]},
            {"api_id": "KA10080", "title": "주식분봉차트조회요청", "category": "OHLCV_CHART", "maps_to": ["CANONICAL_OHLCV"]},
            {"api_id": "KA10081", "title": "주식일봉차트조회요청", "category": "OHLCV_CHART", "maps_to": ["CANONICAL_OHLCV"]},
            {"api_id": "KA00198", "title": "실시간종목조회순위", "category": "RANKING_OUTLIER", "maps_to": ["CANONICAL_RANK_SIGNAL"]},
            {"api_id": "KA10023", "title": "거래량급증요청", "category": "RANKING_OUTLIER", "maps_to": ["CANONICAL_RANK_SIGNAL"]},
            {"api_id": "KA10008", "title": "주식외국인종목별매매동향", "category": "FLOW_SHORT_PROGRAM", "maps_to": ["CANONICAL_FLOW_SIGNAL"]},
            {"api_id": "KA90003", "title": "프로그램순매수상위50요청", "category": "FLOW_SHORT_PROGRAM", "maps_to": ["CANONICAL_FLOW_SIGNAL"]},
            {"api_id": "KA20001", "title": "업종현재가요청", "category": "SECTOR_THEME_ETF", "maps_to": ["CANONICAL_SECTOR_THEME_SIGNAL"]},
            {"api_id": "KA90001", "title": "테마그룹별요청", "category": "SECTOR_THEME_ETF", "maps_to": ["CANONICAL_SECTOR_THEME_SIGNAL"]},
            {"api_id": "KA40003", "title": "ETF일별추이요청", "category": "SECTOR_THEME_ETF", "maps_to": ["CANONICAL_SECTOR_THEME_SIGNAL"]},
            {"api_id": "0B", "title": "주식체결", "category": "REALTIME_READONLY", "maps_to": ["CANONICAL_REALTIME_EVENT"], "realtime_stream": True},
            {"api_id": "0D", "title": "주식호가잔량", "category": "REALTIME_READONLY", "maps_to": ["CANONICAL_REALTIME_EVENT"], "realtime_stream": True},
        ],
        "ls_future_placeholder": {
            "expected_base_url_placeholder": "LS_BASE_URL_PLACEHOLDER",
            "expected_rest_header_shape_placeholder": "LS_HEADER_SHAPE_PLACEHOLDER",
            "expected_tr_code_shape_placeholder": "LS_TR_CODE_PLACEHOLDER",
            "migration_readiness_status": "EVIDENCE_REQUIRED",
        },
        "canonical_quotes": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA10004",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T09:30:00+09:00",
                "available_at": "2026-06-25T09:30:01+09:00",
                "source_ref": "fixtures/provider/kiwoom_quote.json",
                "quality_flags": ["TOKEN_REF_ONLY", "READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "last_price": 82500.0,
            }
        ],
        "canonical_ohlcv_records": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA10081",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:35:00+09:00",
                "source_ref": "fixtures/provider/kiwoom_ohlcv.json",
                "quality_flags": ["POINT_IN_TIME_SAFE"],
                "raw_payload_redacted": True,
                "interval": "1D",
                "open_price": 82000.0,
                "high_price": 83000.0,
                "low_price": 81800.0,
                "close_price": 82500.0,
                "volume": 1234567.0,
            }
        ],
        "canonical_rank_signals": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA00198",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T09:31:00+09:00",
                "available_at": "2026-06-25T09:31:02+09:00",
                "source_ref": "fixtures/provider/kiwoom_rank.json",
                "quality_flags": ["READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "rank_metric": "VOLUME_SPIKE",
                "rank_value": 4.2,
                "rank_order": 3,
            }
        ],
        "canonical_flow_signals": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA10008",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T15:31:00+09:00",
                "available_at": "2026-06-25T15:32:00+09:00",
                "source_ref": "fixtures/provider/kiwoom_flow.json",
                "quality_flags": ["READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "flow_metric": "FOREIGN_NET_FLOW",
                "net_flow_value": 1300000000.0,
            }
        ],
        "canonical_sector_theme_signals": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA20001",
                "canonical_instrument_key": "SEMICONDUCTOR_THEME",
                "provider_symbol": "SEMIS",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T09:32:00+09:00",
                "available_at": "2026-06-25T09:32:05+09:00",
                "source_ref": "fixtures/provider/kiwoom_sector.json",
                "quality_flags": ["READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "sector_or_theme_id": "SEMIS",
                "signal_metric": "RELATIVE_STRENGTH",
                "signal_value": 1.7,
            }
        ],
        "canonical_realtime_events": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "0B",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T09:30:05+09:00",
                "available_at": "2026-06-25T09:30:05+09:00",
                "source_ref": "fixtures/provider/kiwoom_realtime_event.json",
                "quality_flags": ["READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "event_code": "0B",
                "event_type": "TRADE_PRINT",
                "event_summary": "stock trade print",
            }
        ],
        "canonical_capability_records": [
            {
                "provider": "KIWOOM_REST",
                "provider_api_id": "KA10081",
                "canonical_instrument_key": "CAPABILITY_KRX_OHLCV",
                "provider_symbol": "KRX_OHLCV",
                "market": "KRX",
                "currency": "KRW",
                "observed_at": "2026-06-25T09:00:00+09:00",
                "available_at": "2026-06-25T09:00:00+09:00",
                "source_ref": "fixtures/provider/kiwoom_capability.json",
                "quality_flags": ["READ_ONLY_ONLY"],
                "raw_payload_redacted": True,
                "capability_name": "DOMESTIC_OHLCV",
                "capability_status": "AVAILABLE_NOW",
                "notes": "kiwoom chart api available",
            }
        ],
        "blocked_account_order_api_records": [
            {"api_id": "KA00001", "title": "계좌번호조회", "block_reason": "ACCOUNT_API_BLOCKED"},
            {"api_id": "KT10000", "title": "주문요청", "block_reason": "ORDER_API_BLOCKED"},
            {"api_id": "00", "title": "주문체결", "block_reason": "REALTIME_ORDER_STREAM_BLOCKED", "realtime_stream": True},
            {"api_id": "04", "title": "잔고", "block_reason": "REALTIME_ACCOUNT_STREAM_BLOCKED", "realtime_stream": True},
        ],
        "external_gap_markets": ["NQ_ES_FUTURES", "VIX_DXY_10Y_USDKRW", "ECONOMIC_CALENDAR"],
        "safety_report": {
            "safety_report_id": "read-only-provider-adapter-safety-1",
            "blocked_capabilities": [
                "KIWOOM_API_CALL_BLOCKED",
                "LS_API_CALL_BLOCKED",
                "NETWORK_BLOCKED",
                "CREDENTIAL_READ_BLOCKED",
                "TOKEN_LOADING_BLOCKED",
                "AUTH_HEADER_GENERATION_BLOCKED",
                "ACCOUNT_ORDER_API_BLOCKED",
            ],
            "findings": [],
        },
        "audit_records": [
            {
                "audit_record_id": "read-only-provider-adapter-audit-1",
                "created_at": "2026-06-25T10:00:00+09:00",
                "source_path": "fixtures/provider/read_only_provider_adapter_fixture.json",
                "operator_context": "offline kiwoom first readonly boundary review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_provider_adapter_boundary_is_local_offline_report_only():
    loaded = ReadOnlyProviderAdapterInput.model_validate(read_only_provider_adapter_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_network is True


def test_kiwoom_is_current_primary_and_ls_is_future_target():
    loaded = ReadOnlyProviderAdapterInput.model_validate(read_only_provider_adapter_payload())
    provider_map = {item.provider: item for item in loaded.provider_definitions}
    assert provider_map[ReadOnlyProvider.KIWOOM_REST].role == ProviderRole.CURRENT_PRIMARY
    assert provider_map[ReadOnlyProvider.LS_OPEN_API].role == ProviderRole.FUTURE_MIGRATION_TARGET


def test_raw_secret_token_account_auth_markers_are_rejected():
    with pytest.raises(ValueError):
        validate_read_only_provider_adapter_metadata_safety({"authorization": "Bearer real-token"}, context="provider boundary")
    with pytest.raises(ValueError):
        validate_read_only_provider_adapter_metadata_safety({"api_key": "secret"}, context="provider boundary")


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "read_only_provider_adapter_fixture.json"
    fixture_path.write_text(json.dumps(read_only_provider_adapter_payload()), encoding="utf-8")
    loaded = load_read_only_provider_adapter_fixture(fixture_path)
    assert isinstance(loaded, ReadOnlyProviderAdapterInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_read_only_provider_adapter_fixture("https://example.com/kiwoom_provider.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_read_only_provider_adapter_fixture(tmp_path / "provider.parquet")


def test_request_envelope_uses_token_ref_only_and_no_auth_generation():
    loaded = ReadOnlyProviderAdapterInput.model_validate(read_only_provider_adapter_payload())
    assert loaded.request_envelope_boundary.authorization_template == "Bearer <TOKEN_REF_ONLY>"
    assert loaded.request_envelope_boundary.no_auth_header_generation is True
