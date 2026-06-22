from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.kiwoom_mock_api_transport_draft_models import (
    KiwoomMockApiTransportDraftConfig,
)


def load_kiwoom_mock_api_transport_draft_fixture(path) -> KiwoomMockApiTransportDraftConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("kiwoom mock api transport draft fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("kiwoom mock api transport draft fixture must be an explicit local JSON file")
        return KiwoomMockApiTransportDraftConfig.model_validate_json(
            fixture_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ValueError(f"invalid kiwoom mock api transport draft fixture at {source_path}: {exc}") from exc
