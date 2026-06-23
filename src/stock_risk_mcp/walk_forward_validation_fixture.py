from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.walk_forward_validation_models import WalkForwardValidationInput


def load_walk_forward_validation_fixture(path) -> WalkForwardValidationInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("walk forward validation fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("walk forward validation fixture must be an explicit local JSON file")
        return WalkForwardValidationInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid walk forward validation fixture at {source_path}: {exc}") from exc
