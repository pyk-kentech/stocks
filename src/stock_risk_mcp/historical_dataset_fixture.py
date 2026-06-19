from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_dataset_models import HistoricalDatasetAssemblyInput


def load_historical_dataset_fixture(path) -> HistoricalDatasetAssemblyInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("historical dataset fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("historical dataset fixture must be an explicit local JSON file")
        return HistoricalDatasetAssemblyInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical dataset fixture at {source_path}: {exc}") from exc
