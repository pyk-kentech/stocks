from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.cnn_fear_greed_models import CNNFearGreedCollectorConfig


def load_cnn_fear_greed_fixture(path) -> CNNFearGreedCollectorConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("cnn fear greed fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("cnn fear greed fixture must be an explicit local JSON file")
        return CNNFearGreedCollectorConfig.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid cnn fear greed fixture at {source_path}: {exc}") from exc
