from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_outcome_models import HistoricalOutcomeObservationInput


def load_historical_outcome_fixture(path) -> HistoricalOutcomeObservationInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("historical outcome fixture must be an explicit local JSON file")
        return HistoricalOutcomeObservationInput.model_validate_json(
            fixture_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ValueError(f"invalid historical outcome fixture at {source_path}: {exc}") from exc
