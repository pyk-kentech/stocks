import json

import pytest

from stock_risk_mcp.market_regime_fixture import load_market_regime_fixture
from stock_risk_mcp.market_regime_guard import validate_market_regime_metadata_safety
from stock_risk_mcp.market_regime_models import (
    MarketRegimeDecision,
    MarketRegimeInput,
    MarketRiskAppetite,
    MarketVolatilityState,
)


def market_regime_payload(**overrides):
    payload = {
        "regime_id": "market-regime-1",
        "snapshot": {
            "snapshot_id": "market-regime-snapshot-1",
            "anchor_at": "2026-06-24T09:10:00+09:00",
            "observed_at": "2026-06-24T09:00:00+09:00",
            "available_at": "2026-06-24T09:05:00+09:00",
            "nq": {"symbol": "NQ", "last_value": 20000.0, "pct_change_1d": 0.8, "source_ref": "fixtures/market/nq.json"},
            "es": {"symbol": "ES", "last_value": 5500.0, "pct_change_1d": 0.6, "source_ref": "fixtures/market/es.json"},
            "vix": {"symbol": "VIX", "last_value": 14.5, "pct_change_1d": -4.0, "source_ref": "fixtures/market/vix.json"},
            "dxy": {"symbol": "DXY", "last_value": 104.0, "pct_change_1d": -0.3, "source_ref": "fixtures/market/dxy.json"},
            "us10y": {"symbol": "US10Y", "last_value": 4.2, "pct_change_1d": -0.8, "source_ref": "fixtures/market/us10y.json"},
            "usdkrw": {"symbol": "USDKRW", "last_value": 1360.0, "pct_change_1d": -0.2, "source_ref": "fixtures/market/usdkrw.json"},
            "cnn_fear_greed_feature_ref": "fixtures/cnn/cnn_fear_greed_feature.json",
            "data_freshness_policy": {"max_age_minutes": 90, "critical_inputs": ["NQ", "ES", "VIX", "DXY", "US10Y", "USDKRW"]},
        },
        "audit_records": [
            {
                "audit_record_id": "market-regime-audit-1",
                "created_at": "2026-06-24T09:11:00+09:00",
                "source_path": "fixtures/market/market_regime_fixture.json",
                "operator_context": "offline market regime review",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_default_market_regime_is_local_offline_report_only():
    loaded = MarketRegimeInput.model_validate(market_regime_payload())
    assert loaded.report_only is True
    assert loaded.offline_only is True
    assert loaded.no_order is True


def test_guard_rejects_secret_token_account_markers():
    with pytest.raises(ValueError):
        validate_market_regime_metadata_safety({"authorization": "Bearer secret"}, context="market regime")


def test_fixture_loader_reads_local_json_only(tmp_path):
    path = tmp_path / "market_regime_fixture.json"
    path.write_text(json.dumps(market_regime_payload()), encoding="utf-8")
    loaded = load_market_regime_fixture(path)
    assert isinstance(loaded, MarketRegimeInput)
    assert loaded.local_file_only is True


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_market_regime_fixture("https://example.com/market_regime.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_market_regime_fixture(tmp_path / "market_regime.parquet")


def test_decision_and_regime_surfaces():
    assert MarketRegimeDecision.TRAINING_FEATURE_READY.value == "TRAINING_FEATURE_READY"
    assert MarketRiskAppetite.RISK_ON.value == "RISK_ON"
    assert MarketVolatilityState.HIGH_VOL.value == "HIGH_VOL"
