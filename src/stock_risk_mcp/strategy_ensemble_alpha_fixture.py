from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.strategy_ensemble_alpha_models import StrategyEnsembleAlphaInput


def load_strategy_ensemble_alpha_fixture(path) -> StrategyEnsembleAlphaInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("strategy ensemble alpha fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("strategy ensemble alpha fixture must be an explicit local JSON file")
        return StrategyEnsembleAlphaInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid strategy ensemble alpha fixture at {source_path}: {exc}") from exc
