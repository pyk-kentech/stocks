from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.breadth_leadership_routing_models import BreadthLeadershipRoutingInput


def load_breadth_leadership_routing_fixture(path) -> BreadthLeadershipRoutingInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("breadth leadership routing fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("breadth leadership routing fixture must be an explicit local JSON file")
        return BreadthLeadershipRoutingInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid breadth leadership routing fixture at {source_path}: {exc}") from exc
