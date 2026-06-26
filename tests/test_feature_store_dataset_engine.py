from pathlib import Path

from stock_risk_mcp.feature_store_integration_engine import build_feature_store_pipeline
from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput, FeatureStoreReadinessStatus
from tests.test_feature_store_models import feature_store_payload


def test_feature_store_pipeline_derives_labels_and_training_manifest():
    result = build_feature_store_pipeline(
        FeatureStorePipelineInput.model_validate(feature_store_payload()),
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert result.label_rows
    assert result.training_rows
    assert result.training_dataset_manifest.readiness_status == FeatureStoreReadinessStatus.LABELED_DATASET_READY
    first_label = result.label_rows[0]
    assert first_label.anchor_price is not None
    assert first_label.anchor_available_at <= first_label.label_available_at
    assert first_label.label_available_at > first_label.anchor_available_at
    assert result.training_readiness_report.readiness_status == FeatureStoreReadinessStatus.LABELED_DATASET_READY


def test_feature_store_pipeline_blocks_label_like_feature_names():
    payload = feature_store_payload()
    payload["source_feature_inputs"][0]["feature_values"]["forward_return"] = 0.5
    result = build_feature_store_pipeline(
        FeatureStorePipelineInput.model_validate(payload),
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert result.leakage_report.readiness_status == FeatureStoreReadinessStatus.BLOCKED_LEAKAGE
    assert "LABEL_LIKE_FEATURE_NAME" in result.leakage_report.leakage_categories
