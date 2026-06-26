from stock_risk_mcp.feature_store_cache_engine import build_feature_store_cache
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput, FeatureStoreReadinessStatus
from tests.test_feature_store_models import feature_store_payload


def test_feature_store_cache_builds_feature_rows_and_schema():
    pipeline_input = FeatureStorePipelineInput.model_validate(feature_store_payload())
    feature_rows, feature_schema, cache_manifest, completeness_report, freshness_report, gap_report = build_feature_store_cache(pipeline_input)

    assert len(feature_rows) == 20
    assert feature_schema.columns
    assert cache_manifest.cached_row_count == 20
    assert "V8_DOMESTIC_STOCK_SNAPSHOT" in completeness_report.present_source_kinds
    assert freshness_report.latest_feature_asof is not None
    assert gap_report.readiness_status == FeatureStoreReadinessStatus.FEATURE_ROWS_READY
