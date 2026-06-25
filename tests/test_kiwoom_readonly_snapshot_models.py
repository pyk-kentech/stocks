import json

import pytest

from stock_risk_mcp.kiwoom_readonly_snapshot_fixture import load_kiwoom_readonly_snapshot_fixture
from stock_risk_mcp.kiwoom_readonly_snapshot_guard import validate_kiwoom_readonly_snapshot_metadata_safety
from stock_risk_mcp.kiwoom_readonly_snapshot_models import (
    KiwoomReadonlySnapshotConfig,
    KiwoomReadonlySnapshotReadiness,
)


def kiwoom_readonly_snapshot_payload(**overrides):
    payload = {
        "config_id": "SNAPSHOT-001",
        "available_at": "2026-06-25T15:30:00+09:00",
        "source_ref": "fixtures/kiwoom_readonly_snapshot_fixture.json",
        "operator_context": "v8.6 snapshot fixture",
        "canonical_ohlcv_records": [
            {
                "provider_api_id": "KA10081",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "timeframe": "D1",
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "open": 80000,
                "high": 81000,
                "low": 79000,
                "close": 80500,
                "volume": 1500000,
                "source_ref": "fixtures/chart.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_rank_signals": [
            {
                "provider_api_id": "KA00198",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:20:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "rank_type": "VOLUME_TOP",
                "rank": 3,
                "price": 80500,
                "price_change": 1000,
                "percent_change": 1.26,
                "volume": 1400000,
                "trading_value": 112000000000,
                "relative_volume": 1.4,
                "liquidity_evidence_flag": True,
                "outlier_category": "UNKNOWN",
                "source_ref": "fixtures/rank.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_outlier_signals": [
            {
                "provider_api_id": "KA10023",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:20:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "rank_type": "PRICE_MOMENTUM",
                "rank": 7,
                "price": 80500,
                "price_change": 1000,
                "percent_change": 1.26,
                "volume": 1400000,
                "trading_value": 112000000000,
                "relative_volume": 1.4,
                "liquidity_evidence_flag": True,
                "outlier_category": "PRICE_SURGE",
                "source_ref": "fixtures/outlier.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_quote_records": [
            {
                "provider_api_id": "KA10003",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:20:05+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "last_price": 80500,
                "bid_price": 80500,
                "ask_price": 80600,
                "bid_quantity": 1200,
                "ask_quantity": 900,
                "spread": 100,
                "mid_price": 80550,
                "last_trade_quantity": 100,
                "percent_change": 1.26,
                "price_change": 1000,
                "liquidity_evidence_flag": True,
                "source_ref": "fixtures/quote.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_orderbook_records": [
            {
                "provider_api_id": "KA10004",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:20:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "levels": [{"side": "ASK", "level": 1, "price": 80600, "quantity": 900}, {"side": "BID", "level": 1, "price": 80500, "quantity": 1200}],
                "spread": 100,
                "mid_price": 80550,
                "top_of_book_imbalance": 0.14,
                "depth_summary_quantity": 2100,
                "source_ref": "fixtures/orderbook.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_liquidity_hints": [
            {
                "provider_api_id": "KA10004",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:20:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "spread": 100,
                "mid_price": 80550,
                "last_trade_quantity": 100,
                "top_of_book_imbalance": 0.14,
                "price_liquidity_ready": True,
                "outlier_routing_ready": True,
                "mock_intent_preview_ready": True,
                "source_ref": "fixtures/liquidity.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_basic_info_records": [
            {
                "provider_api_id": "KA10001",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "available_at": "2026-06-25T15:30:00+09:00",
                "settlement_month": "12",
                "listed_shares": 5969782550,
                "market_cap": 480000000000000,
                "market_cap_weight": 17.5,
                "source_ref": "fixtures/basic_info.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_investor_flow_signals": [
            {
                "provider_api_id": "KA10059",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "flow_category": "FOREIGN",
                "net_buy_amount": 15000000000,
                "net_buy_quantity": 180000,
                "confidence_flags": ["CANONICAL_FLOW"],
                "source_ref": "fixtures/investor_flow.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_program_flow_signals": [
            {
                "provider_api_id": "KA90003",
                "canonical_instrument_key": "005930_KRX",
                "provider_symbol": "005930",
                "stock_name": "삼성전자",
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "flow_category": "PROGRAM",
                "program_buy_amount": 7000000000,
                "program_sell_amount": 5000000000,
                "program_net_amount": 2000000000,
                "confidence_flags": ["PROGRAM_FLOW"],
                "source_ref": "fixtures/program_flow.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_theme_leadership_signals": [
            {
                "provider_api_id": "KA90001",
                "theme_group_code": "553",
                "theme_name": "AI반도체",
                "stock_count": 12,
                "rising_stock_count": 9,
                "falling_stock_count": 3,
                "theme_change_rate": 2.5,
                "period_return": 4.3,
                "main_stock": "삼성전자",
                "participation_hint": 0.75,
                "concentration_hint": 0.3,
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "source_ref": "fixtures/theme_leadership.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_theme_membership_signals": [
            {
                "provider_api_id": "KA90002",
                "theme_group_code": "553",
                "theme_name": "AI반도체",
                "component_stock_code": "005930",
                "component_stock_name": "삼성전자",
                "component_change_rate": 2.1,
                "component_return": 4.0,
                "membership_evidence_flag": True,
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "source_ref": "fixtures/theme_membership.json",
            }
        ],
        "canonical_etf_trend_signals": [
            {
                "provider_api_id": "KA40003",
                "etf_stock_code": "069500",
                "date": "20260625",
                "price": 38.2,
                "previous_close_difference": 0.15,
                "percent_change": 0.39,
                "trend_direction": "UP",
                "observed_at": "2026-06-25T15:30:00+09:00",
                "available_at": "2026-06-25T15:30:00+09:00",
                "source_ref": "fixtures/etf_trend.json",
                "quality_flags": ["READ_ONLY_ONLY"],
            }
        ],
        "canonical_sector_capability_signals": [
            {
                "api_id": "KA90001",
                "capability_group": "THEME",
                "request_builder_ready": True,
                "readiness": "THEME_LEADERSHIP_READY",
            }
        ],
        "safety_report": {
            "safety_report_id": "SNAPSHOT-001-SAFETY-REPORT",
        },
        "audit_records": [
            {
                "audit_record_id": "SNAPSHOT-001-AUDIT",
                "created_at": "2026-06-25T15:31:00+09:00",
                "source_path": "fixtures/kiwoom_readonly_snapshot_fixture.json",
                "operator_context": "v8.6 snapshot fixture",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_snapshot_config_validates_canonical_bundle():
    loaded = KiwoomReadonlySnapshotConfig.model_validate(kiwoom_readonly_snapshot_payload())
    assert loaded.config_id == "SNAPSHOT-001"
    assert loaded.safety_report.safety_report_id == "SNAPSHOT-001-SAFETY-REPORT"
    assert loaded.canonical_quote_records[0].provider_symbol == "005930"


def test_snapshot_fixture_loader_accepts_local_json(tmp_path):
    fixture_path = tmp_path / "kiwoom_readonly_snapshot_fixture.json"
    fixture_path.write_text(json.dumps(kiwoom_readonly_snapshot_payload()), encoding="utf-8")
    loaded = load_kiwoom_readonly_snapshot_fixture(fixture_path)
    assert loaded.config_id == "SNAPSHOT-001"


def test_snapshot_guard_rejects_remote_or_blank_metadata():
    validate_kiwoom_readonly_snapshot_metadata_safety(
        {"source_path": "fixtures/example.json", "operator_context": "snapshot"},
        context="snapshot metadata",
    )
    with pytest.raises(ValueError):
        validate_kiwoom_readonly_snapshot_metadata_safety(
            {"source_path": "https://example.com/a.json", "operator_context": "snapshot"},
            context="snapshot metadata",
        )
    with pytest.raises(ValueError):
        validate_kiwoom_readonly_snapshot_metadata_safety(
            {"source_path": "fixtures/example.json", "operator_context": ""},
            context="snapshot metadata",
        )


def test_snapshot_fixture_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError):
        load_kiwoom_readonly_snapshot_fixture("https://example.com/snapshot.json")
    with pytest.raises(ValueError):
        load_kiwoom_readonly_snapshot_fixture(tmp_path / "snapshot.parquet")


def test_snapshot_readiness_enum_contains_expected_values():
    assert {
        KiwoomReadonlySnapshotReadiness.SNAPSHOT_READY.value,
        KiwoomReadonlySnapshotReadiness.PARTIAL.value,
        KiwoomReadonlySnapshotReadiness.STALE.value,
        KiwoomReadonlySnapshotReadiness.CONFLICT.value,
        KiwoomReadonlySnapshotReadiness.DATA_GAP.value,
    }
