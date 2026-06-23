from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.point_in_time_universe_models import PointInTimeUniverseInput


def load_point_in_time_universe_fixture(path) -> PointInTimeUniverseInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("point in time universe fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("point in time universe fixture must be an explicit local JSON file")
        return PointInTimeUniverseInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid point in time universe fixture at {source_path}: {exc}") from exc
