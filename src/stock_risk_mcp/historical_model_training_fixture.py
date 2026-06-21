from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_model_training_models import HistoricalModelTrainingInput


def load_historical_model_training_fixture(path) -> HistoricalModelTrainingInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("historical model training fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("historical model training fixture must be an explicit local JSON file")
        return HistoricalModelTrainingInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical model training fixture at {source_path}: {exc}") from exc
