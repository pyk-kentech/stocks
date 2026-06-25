from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.kiwoom_readonly_snapshot_models import KiwoomReadonlySnapshotConfig


def load_kiwoom_readonly_snapshot_fixture(path) -> KiwoomReadonlySnapshotConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("kiwoom readonly snapshot fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("kiwoom readonly snapshot fixture must be an explicit local JSON file")
        return KiwoomReadonlySnapshotConfig.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid kiwoom readonly snapshot fixture at {source_path}: {exc}") from exc
