from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.offline_strategy_models import OfflineStrategyPipelineInput


def load_offline_strategy_fixture(path) -> OfflineStrategyPipelineInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("offline strategy fixture must be a local file path")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("offline strategy fixture must be an explicit local JSON file")
        return OfflineStrategyPipelineInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid offline strategy fixture at {source_path}: {exc}") from exc
