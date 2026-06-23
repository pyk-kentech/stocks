from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.training_pipeline_promotion_models import TrainingPipelinePromotionInput


def load_training_pipeline_promotion_fixture(path) -> TrainingPipelinePromotionInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("training pipeline promotion fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("training pipeline promotion fixture must be an explicit local JSON file")
        return TrainingPipelinePromotionInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid training pipeline promotion fixture at {source_path}: {exc}") from exc
