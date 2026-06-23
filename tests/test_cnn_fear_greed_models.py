import json

import pytest

from stock_risk_mcp.cnn_fear_greed_fixture import load_cnn_fear_greed_fixture
from stock_risk_mcp.cnn_fear_greed_guard import validate_cnn_fear_greed_metadata_safety
from stock_risk_mcp.cnn_fear_greed_models import (
    CNNFearGreedCategory,
    CNNFearGreedCollectorConfig,
    CNNFearGreedGapCategory,
)


def cnn_fear_greed_fixture_payload(mock_payload=None, **overrides):
    payload = {
        "config_id": "cnn-fear-greed-config-1",
        "source_url": "https://edition.cnn.com/markets/fear-and-greed",
        "enabled": False,
        "execute_collection": False,
        "acknowledge_collection": False,
        "allow_real_network": False,
        "transport_mode": "MOCKED_HTTP",
        "timeout_seconds": 5,
        "max_retry_count": 1,
        "max_requests_per_run": 1,
        "min_collection_interval_seconds": 3600,
        "cache_metadata_policy": "REPORT_ONLY",
        "source_health_reporting": True,
        "mock_payload": mock_payload
        or {
            "score": 22,
            "label": "Extreme Fear",
            "as_of": "2026-06-24T09:00:00+09:00",
            "available_at": "2026-06-24T09:05:00+09:00",
            "components": {
                "stock_price_strength": 31,
                "stock_price_breadth": 27,
            },
            "history": [
                {"as_of": "2026-06-23T09:00:00+09:00", "score": 30},
                {"as_of": "2026-06-24T09:00:00+09:00", "score": 22},
            ],
            "schema_version": "cnn-fg-v1",
        },
    }
    payload.update(overrides)
    return payload


def test_default_collector_is_disabled_dry_run_and_mock_only():
    config = CNNFearGreedCollectorConfig.model_validate(cnn_fear_greed_fixture_payload())
    assert config.enabled is False
    assert config.execute_collection is False
    assert config.allow_real_network is False
    assert config.transport_mode == "MOCKED_HTTP"
    assert config.non_executable is True


def test_required_safety_flags_are_true():
    config = CNNFearGreedCollectorConfig.model_validate(cnn_fear_greed_fixture_payload())
    assert config.report_only is True
    assert config.no_trading_path is True
    assert config.no_order is True
    assert config.no_account_mutation is True
    assert config.no_broker_api is True
    assert config.no_cloud_llm is True
    assert config.no_local_llm_runtime is True


def test_mock_endpoint_refs_are_evidence_only_and_non_executable():
    config = CNNFearGreedCollectorConfig.model_validate(cnn_fear_greed_fixture_payload())
    assert config.source_url == "https://edition.cnn.com/markets/fear-and-greed"
    assert config.allow_real_network is False


def test_guard_rejects_raw_secret_token_account_auth_markers():
    with pytest.raises(ValueError):
        validate_cnn_fear_greed_metadata_safety(
            {"authorization": "Bearer abc"},
            context="cnn fear greed",
        )


def test_fixture_loader_reads_local_json_only(tmp_path):
    fixture_path = tmp_path / "cnn_fear_greed_fixture.json"
    fixture_path.write_text(json.dumps(cnn_fear_greed_fixture_payload()), encoding="utf-8")
    loaded = load_cnn_fear_greed_fixture(fixture_path)
    assert isinstance(loaded, CNNFearGreedCollectorConfig)
    assert loaded.transport_mode == "MOCKED_HTTP"


def test_fixture_loader_rejects_remote_or_parquet(tmp_path):
    with pytest.raises(ValueError, match="local file path"):
        load_cnn_fear_greed_fixture("https://example.com/cnn.json")
    with pytest.raises(ValueError, match="parquet remains unsupported"):
        load_cnn_fear_greed_fixture(tmp_path / "cnn.parquet")


def test_category_enum_surface():
    assert CNNFearGreedCategory.EXTREME_FEAR.value == "EXTREME_FEAR"
    assert CNNFearGreedCategory.UNKNOWN.value == "UNKNOWN"


def test_gap_categories_include_schema_mismatch_and_source_health():
    categories = {item.value for item in CNNFearGreedGapCategory}
    assert "SCHEMA_MISMATCH" in categories
    assert "SOURCE_HEALTH_WARNING" in categories
