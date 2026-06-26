from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.feature_store_models import FeatureStorePipelineInput


def load_feature_store_fixture(path) -> FeatureStorePipelineInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("feature store fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("feature store fixture must be an explicit local JSON file")
        return FeatureStorePipelineInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid feature store fixture at {source_path}: {exc}") from exc
