from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.kiwoom_mock_api_preflight_gate_models import (
    KiwoomMockApiPreflightGateConfig,
)


def load_kiwoom_mock_api_preflight_gate_fixture(path) -> KiwoomMockApiPreflightGateConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("kiwoom mock api preflight gate fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("kiwoom mock api preflight gate fixture must be an explicit local JSON file")
        return KiwoomMockApiPreflightGateConfig.model_validate_json(
            fixture_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ValueError(f"invalid kiwoom mock api preflight gate fixture at {source_path}: {exc}") from exc
