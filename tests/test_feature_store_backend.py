from pathlib import Path

from stock_risk_mcp.feature_store_backend import (
    build_feature_store_backend_capability_report,
    materialize_feature_store_manifest,
)
from stock_risk_mcp.feature_store_integration_engine import build_feature_store_pipeline
from stock_risk_mcp.feature_store_models import FeatureStoreBackend, FeatureStoreBackendStatus, FeatureStorePipelineInput
from tests.test_feature_store_models import feature_store_payload


def test_feature_store_backend_report_and_materialization(tmp_path):
    payload = feature_store_payload(store_root=str(tmp_path / "feature_store"))
    pipeline_input = FeatureStorePipelineInput.model_validate(payload)
    repo_root = Path(__file__).resolve().parents[1]
    capability = build_feature_store_backend_capability_report(pipeline_input, repo_root=repo_root)
    json_row = next(row for row in capability.rows if row.backend == FeatureStoreBackend.JSON)
    assert json_row.status == FeatureStoreBackendStatus.AVAILABLE

    result = build_feature_store_pipeline(pipeline_input, repo_root=repo_root)
    materialized = materialize_feature_store_manifest(
        pipeline_input,
        result.training_dataset_manifest,
        result.training_rows,
        repo_root=repo_root,
        capability_report=capability,
    )
    assert materialized.status in {FeatureStoreBackendStatus.AVAILABLE, FeatureStoreBackendStatus.DEPENDENCY_GAP}
    assert all(Path(path).exists() for path in materialized.materialized_paths)
