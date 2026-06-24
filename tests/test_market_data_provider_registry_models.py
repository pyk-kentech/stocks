import json

import pytest

from stock_risk_mcp.market_data_provider_registry_fixture import load_market_data_provider_registry_fixture
from stock_risk_mcp.market_data_provider_registry_guard import validate_market_data_provider_registry_metadata_safety
from stock_risk_mcp.market_data_provider_registry_models import (
    DataClass,
    MarketDataProviderRegistryInput,
    ModuleName,
    ProviderCandidateName,
    ProviderReadinessLevel,
)


def market_data_provider_registry_payload(**overrides):
    payload = {
        "registry_id": "provider-registry-1",
        "provider_candidates": [
            {
                "provider_name": "LOCAL_FIXTURE",
                "provider_type": "LOCAL",
                "access_mode": "LOCAL",
                "official": False,
                "unofficial": False,
                "internal": True,
                "delayed": False,
                "historical_support": True,
                "live_support": False,
                "delayed_support": False,
                "read_only_support": True,
                "api_key_required": False,
                "subscription_required": False,
                "license_terms_note_ref": "docs/licenses/local_fixture.md",
                "latency_class": "OFFLINE",
                "expected_freshness": "FIXTURE_STATIC",
                "allowed_use_cases": ["DEVELOPMENT", "TESTING"],
                "disallowed_use_cases": ["LIVE_READ_ONLY"],
                "implementation_status": "ACTIVE",
                "risk_note": "local fixture only",
                "readiness_level": "FIXTURE_ONLY",
            },
            {
                "provider_name": "DATABENTO",
                "provider_type": "API",
                "access_mode": "PAID",
                "official": True,
                "unofficial": False,
                "internal": False,
                "delayed": False,
                "historical_support": True,
                "live_support": False,
                "delayed_support": False,
                "read_only_support": True,
                "api_key_required": True,
                "subscription_required": True,
                "license_terms_note_ref": "docs/licenses/databento.md",
                "latency_class": "LOW",
                "expected_freshness": "NEAR_REALTIME",
                "allowed_use_cases": ["BACKTEST", "TRAINING"],
                "disallowed_use_cases": ["LIVE_TRADING"],
                "implementation_status": "CANDIDATE",
                "risk_note": "requires subscription evidence",
                "readiness_level": "TRAINING_READY",
                "subscription_evidence_ref": "docs/evidence/databento_subscription.md",
                "api_key_evidence_ref": "docs/evidence/databento_api_key_boundary.md",
            },
            {
                "provider_name": "YAHOO_DELAYED",
                "provider_type": "PUBLIC_WEB",
                "access_mode": "FREE",
                "official": False,
                "unofficial": True,
                "internal": False,
                "delayed": True,
                "historical_support": True,
                "live_support": False,
                "delayed_support": True,
                "read_only_support": True,
                "api_key_required": False,
                "subscription_required": False,
                "license_terms_note_ref": "docs/licenses/yahoo_delayed.md",
                "latency_class": "DELAYED",
                "expected_freshness": "DELAYED",
                "allowed_use_cases": ["SANITY_CHECK"],
                "disallowed_use_cases": ["TRAINING", "LIVE_READ_ONLY"],
                "implementation_status": "CANDIDATE",
                "risk_note": "delayed only",
                "readiness_level": "SANITY_CHECK_ONLY",
            },
            {
                "provider_name": "MANUAL_CSV",
                "provider_type": "MANUAL",
                "access_mode": "MANUAL",
                "official": False,
                "unofficial": False,
                "internal": True,
                "delayed": False,
                "historical_support": True,
                "live_support": False,
                "delayed_support": False,
                "read_only_support": True,
                "api_key_required": False,
                "subscription_required": False,
                "license_terms_note_ref": "docs/licenses/manual_csv.md",
                "latency_class": "OFFLINE",
                "expected_freshness": "MANUAL",
                "allowed_use_cases": ["BACKTEST", "TRAINING"],
                "disallowed_use_cases": ["LIVE_READ_ONLY"],
                "implementation_status": "ACTIVE",
                "risk_note": "requires source and available_at evidence",
                "readiness_level": "BACKTEST_READY",
            },
            {
                "provider_name": "IBKR",
                "provider_type": "BROKER_READONLY",
                "access_mode": "PAID",
                "official": True,
                "unofficial": False,
                "internal": False,
                "delayed": False,
                "historical_support": True,
                "live_support": True,
                "delayed_support": False,
                "read_only_support": True,
                "api_key_required": False,
                "subscription_required": True,
                "license_terms_note_ref": "docs/licenses/ibkr.md",
                "latency_class": "LOW",
                "expected_freshness": "LIVE_READONLY",
                "allowed_use_cases": ["LIVE_READ_ONLY"],
                "disallowed_use_cases": ["LIVE_TRADING"],
                "implementation_status": "CANDIDATE",
                "risk_note": "candidate only, no connection in v7.9.1",
                "readiness_level": "LIVE_READ_ONLY_READY",
                "subscription_evidence_ref": "docs/evidence/ibkr_subscription.md",
            },
        ],
        "module_requirements": [
            {
                "module_name": "MARKET_REGIME_ENGINE",
                "required_data_classes": ["FUTURES", "VOLATILITY_INDEX", "FX", "RATES_YIELDS"],
                "optional_data_classes": ["SENTIMENT_FEAR_INDEX"],
                "minimum_readiness_level": "TRAINING_READY",
                "freshness_requirement": "UNDER_90_MINUTES",
                "available_at_required": True,
                "source_ref_required": True,
                "historical_depth_requirement": "1D_PLUS",
                "training_grade_required": True,
                "live_read_only_required": False,
                "fallback_policy": "GAP_IF_CRITICAL_MISSING",
            },
            {
                "module_name": "POSITION_SIZING_ENGINE",
                "required_data_classes": ["EQUITY_PRICE_OHLCV", "FX", "FEE_TAX_SLIPPAGE", "VOLUME_RELATIVE_VOLUME"],
                "optional_data_classes": ["VOLATILITY_INDEX"],
                "minimum_readiness_level": "PAPER_READY",
                "freshness_requirement": "UNDER_1_DAY",
                "available_at_required": True,
                "source_ref_required": True,
                "historical_depth_requirement": "20D_PLUS",
                "training_grade_required": False,
                "live_read_only_required": False,
                "fallback_policy": "BLOCK_IF_RISK_EVIDENCE_MISSING",
            },
            {
                "module_name": "EVENT_RISK_GATE",
                "required_data_classes": ["ECONOMIC_CALENDAR", "EARNINGS_CALENDAR"],
                "optional_data_classes": ["CORPORATE_ACTIONS"],
                "minimum_readiness_level": "PAPER_READY",
                "freshness_requirement": "SAME_DAY",
                "available_at_required": True,
                "source_ref_required": True,
                "historical_depth_requirement": "EVENT_WINDOW",
                "training_grade_required": False,
                "live_read_only_required": False,
                "fallback_policy": "GAP_IF_EVENT_CALENDAR_MISSING",
            },
            {
                "module_name": "BREADTH_ENGINE",
                "required_data_classes": ["BREADTH_MARKET_INTERNALS"],
                "optional_data_classes": ["BENCHMARK_INDEX_CONSTITUENTS"],
                "minimum_readiness_level": "TRAINING_READY",
                "freshness_requirement": "UNDER_1_DAY",
                "available_at_required": True,
                "source_ref_required": True,
                "historical_depth_requirement": "5D_PLUS",
                "training_grade_required": True,
                "live_read_only_required": False,
                "fallback_policy": "GAP_IF_BREADTH_MISSING",
            },
        ],
        "canonical_contracts": [
            {
                "instrument_key": "NQ_FUTURES_MAIN",
                "provider_symbol": "NQ.c.0",
                "data_class": "FUTURES",
                "observed_at": "2026-06-24T09:00:00+09:00",
                "available_at": "2026-06-24T09:05:00+09:00",
                "value": 20000.0,
                "open": 19920.0,
                "high": 20010.0,
                "low": 19890.0,
                "close": 20000.0,
                "volume": 123456.0,
                "percent_change": 0.8,
                "currency": "USD",
                "market": "CME",
                "timezone": "America/Chicago",
                "data_delay_seconds": 0,
                "source_provider": "DATABENTO",
                "source_ref": "fixtures/provider/nq.json",
                "quality_flags": ["POINT_IN_TIME_SAFE"],
                "stale": False,
                "gap_reason": None,
                "corporate_action_adjusted": False,
                "survivorship_safe": True,
            }
        ],
        "symbol_mappings": [
            {"mapping_id": "MAP-NQ", "canonical_key": "NQ_FUTURES_MAIN", "provider_symbol": "NQ.c.0", "provider_name": "DATABENTO", "data_class": "FUTURES"},
            {"mapping_id": "MAP-ES", "canonical_key": "ES_FUTURES_MAIN", "provider_symbol": "ES.c.0", "provider_name": "DATABENTO", "data_class": "FUTURES"},
            {"mapping_id": "MAP-VIX", "canonical_key": "VIX_INDEX", "provider_symbol": "VIX", "provider_name": "YAHOO_DELAYED", "data_class": "VOLATILITY_INDEX"},
            {"mapping_id": "MAP-DXY", "canonical_key": "DXY_INDEX", "provider_symbol": "DX-Y.NYB", "provider_name": "YAHOO_DELAYED", "data_class": "FX"},
            {"mapping_id": "MAP-10Y", "canonical_key": "US10Y_YIELD", "provider_symbol": "DGS10", "provider_name": "FRED", "data_class": "RATES_YIELDS"},
            {"mapping_id": "MAP-USDKRW", "canonical_key": "USDKRW_SPOT", "provider_symbol": "USDKRW", "provider_name": "ECOS_BOK", "data_class": "FX"},
            {"mapping_id": "MAP-QQQ", "canonical_key": "QQQ_ETF", "provider_symbol": "QQQ", "provider_name": "YAHOO_DELAYED", "data_class": "EQUITY_PRICE_OHLCV"},
            {"mapping_id": "MAP-SPY", "canonical_key": "SPY_ETF", "provider_symbol": "SPY", "provider_name": "YAHOO_DELAYED", "data_class": "EQUITY_PRICE_OHLCV"},
            {"mapping_id": "MAP-KOSPI", "canonical_key": "KOSPI_INDEX", "provider_symbol": "KOSPI", "provider_name": "KRX", "data_class": "BENCHMARK_INDEX_CONSTITUENTS"},
            {"mapping_id": "MAP-KOSDAQ", "canonical_key": "KOSDAQ_INDEX", "provider_symbol": "KOSDAQ", "provider_name": "KRX", "data_class": "BENCHMARK_INDEX_CONSTITUENTS"},
            {"mapping_id": "MAP-005930", "canonical_key": "005930_KRX", "provider_symbol": "005930", "provider_name": "KRX", "data_class": "EQUITY_PRICE_OHLCV"},
            {"mapping_id": "MAP-CNNFG", "canonical_key": "CNN_FEAR_GREED_INDEX", "provider_symbol": "CNN_FG", "provider_name": "CNN_FEAR_GREED", "data_class": "SENTIMENT_FEAR_INDEX"},
            {"mapping_id": "MAP-FOMC", "canonical_key": "FOMC_EVENT", "provider_symbol": "FOMC", "provider_name": "FED", "data_class": "ECONOMIC_CALENDAR"},
            {"mapping_id": "MAP-CPI", "canonical_key": "US_CPI_EVENT", "provider_symbol": "CPI", "provider_name": "BLS", "data_class": "ECONOMIC_CALENDAR"},
            {"mapping_id": "MAP-PCE", "canonical_key": "US_PCE_EVENT", "provider_symbol": "PCE", "provider_name": "BEA", "data_class": "ECONOMIC_CALENDAR"},
            {"mapping_id": "MAP-NFP", "canonical_key": "US_NFP_EVENT", "provider_symbol": "NFP", "provider_name": "BLS", "data_class": "ECONOMIC_CALENDAR"},
            {"mapping_id": "MAP-BOK", "canonical_key": "BOK_RATE_DECISION_EVENT", "provider_symbol": "BOK_BASE_RATE", "provider_name": "ECOS_BOK", "data_class": "ECONOMIC_CALENDAR"},
        ],
        "audit_records": [
            {
                "audit_record_id": "provider-registry-audit-1",
                "created_at": "2026-06-24T18:00:00+09:00",
                "source_path": "fixtures/provider/provider_registry_fixture.json",
                "operator_context": "offline provider registry review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_provider_registry_is_local_offline_report_only():
    loaded = MarketDataProviderRegistryInput.model_validate(market_data_provider_registry_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_network is True


def test_guard_rejects_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_market_data_provider_registry_metadata_safety({"authorization": "Bearer secret"}, context="provider registry")


def test_fixture_loader_reads_local_json_only(tmp_path):
    path = tmp_path / "provider_registry_fixture.json"
    path.write_text(json.dumps(market_data_provider_registry_payload()), encoding="utf-8")
    loaded = load_market_data_provider_registry_fixture(path)
    assert isinstance(loaded, MarketDataProviderRegistryInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_market_data_provider_registry_fixture("https://example.com/provider_registry.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_market_data_provider_registry_fixture(tmp_path / "provider_registry.parquet")


def test_surface_enums_and_module_requirements():
    assert ProviderCandidateName.DATABENTO.value == "DATABENTO"
    assert ProviderReadinessLevel.LIVE_READ_ONLY_READY.value == "LIVE_READ_ONLY_READY"
    assert ModuleName.MARKET_REGIME_ENGINE.value == "MARKET_REGIME_ENGINE"
    assert DataClass.ECONOMIC_CALENDAR.value == "ECONOMIC_CALENDAR"
