from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.event_risk_models import EventRiskInput


def load_event_risk_fixture(path) -> EventRiskInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("event risk fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("event risk fixture must be an explicit local JSON file")
        return EventRiskInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid event risk fixture at {source_path}: {exc}") from exc
