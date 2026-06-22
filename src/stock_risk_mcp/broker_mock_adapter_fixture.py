from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.broker_mock_adapter_models import BrokerMockAdapterInput


def load_broker_mock_adapter_fixture(path) -> BrokerMockAdapterInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("broker mock adapter fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("broker mock adapter fixture must be an explicit local JSON file")
        return BrokerMockAdapterInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid broker mock adapter fixture at {source_path}: {exc}") from exc

