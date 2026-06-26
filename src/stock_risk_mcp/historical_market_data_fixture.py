from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataPipelineInput


def load_historical_market_data_fixture(path) -> HistoricalMarketDataPipelineInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("historical market data fixture must be a local file path")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("historical market data fixture must be an explicit local JSON file")
        return HistoricalMarketDataPipelineInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical market data fixture at {source_path}: {exc}") from exc
