from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.kiwoom_mock_credential_boundary_models import KiwoomMockCredentialBoundaryConfig


def load_kiwoom_mock_credential_boundary_fixture(path) -> KiwoomMockCredentialBoundaryConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("kiwoom mock credential boundary fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("kiwoom mock credential boundary fixture must be an explicit local JSON file")
        return KiwoomMockCredentialBoundaryConfig.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid kiwoom mock credential boundary fixture at {source_path}: {exc}") from exc
