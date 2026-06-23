from stock_risk_mcp.cnn_fear_greed_engine import run_cnn_fear_greed_collection
from stock_risk_mcp.cnn_fear_greed_models import (
    CNNFearGreedCategory,
    CNNFearGreedCollectorConfig,
)
from tests.test_cnn_fear_greed_models import cnn_fear_greed_fixture_payload


def _run(**overrides):
    payload = cnn_fear_greed_fixture_payload()
    payload.update(overrides)
    config = CNNFearGreedCollectorConfig.model_validate(payload)
    return run_cnn_fear_greed_collection(config)


def test_real_collection_requires_explicit_flags():
    config = CNNFearGreedCollectorConfig.model_validate(
        cnn_fear_greed_fixture_payload(enabled=True, execute_collection=True, allow_real_network=True)
    )
    try:
        run_cnn_fear_greed_collection(config)
    except ValueError as exc:
        assert "acknowledge" in str(exc).lower()
    else:
        raise AssertionError("expected explicit opt-in failure")


def test_mocked_payload_parses_score_and_category():
    result = _run()
    assert result.snapshot_report.snapshot.score == 22
    assert result.snapshot_report.snapshot.category == CNNFearGreedCategory.EXTREME_FEAR


def test_historical_data_parses_if_present():
    result = _run()
    assert len(result.history_report.history_points) == 2
    assert result.history_report.history_points[-1].score == 22


def test_category_mapping_works():
    result = _run(mock_payload={**cnn_fear_greed_fixture_payload()["mock_payload"], "score": 68, "label": "Greed"})
    assert result.snapshot_report.snapshot.category == CNNFearGreedCategory.GREED
    assert result.feature_integration_report.sentiment_fear_bucket == "GREED"


def test_malformed_schema_produces_gap_and_source_health_warning():
    result = _run(mock_payload={"unexpected": "payload"})
    assert result.source_health_report.status == "DEGRADED"
    assert "SCHEMA_MISMATCH" in {item.value for item in result.gap_report.gap_categories}


def test_high_frequency_scraping_policy_is_rejected():
    config = CNNFearGreedCollectorConfig.model_validate(
        cnn_fear_greed_fixture_payload(min_collection_interval_seconds=0)
    )
    try:
        run_cnn_fear_greed_collection(config)
    except ValueError as exc:
        assert "low-frequency" in str(exc).lower()
    else:
        raise AssertionError("expected low-frequency policy failure")


def test_feature_integration_emits_v75_v76_compatible_fields():
    result = _run()
    report = result.feature_integration_report
    assert report.cnn_fear_greed_score == 22
    assert report.cnn_fear_greed_category == "EXTREME_FEAR"
    assert report.cnn_fear_greed_available_at == "2026-06-24T09:05:00+09:00"
    assert report.cnn_fear_greed_source_ref == "https://edition.cnn.com/markets/fear-and-greed"


def test_audit_report_is_redacted():
    result = _run()
    assert result.audit_report.redaction_applied is True
    assert result.audit_report.contains_secret_material is False
