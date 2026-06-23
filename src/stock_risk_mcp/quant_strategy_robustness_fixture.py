from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.quant_strategy_robustness_models import QuantStrategyRobustnessInput


def load_quant_strategy_robustness_fixture(path) -> QuantStrategyRobustnessInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("quant strategy robustness fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("quant strategy robustness fixture must be an explicit local JSON file")
        return QuantStrategyRobustnessInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid quant strategy robustness fixture at {source_path}: {exc}") from exc
