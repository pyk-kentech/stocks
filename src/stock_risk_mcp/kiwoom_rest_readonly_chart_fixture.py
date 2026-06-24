from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.kiwoom_rest_readonly_chart_models import KiwoomRestChartConfig


def load_kiwoom_rest_readonly_chart_fixture(path) -> KiwoomRestChartConfig:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("kiwoom rest readonly chart fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("kiwoom rest readonly chart fixture must be an explicit local JSON file")
        return KiwoomRestChartConfig.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid kiwoom rest readonly chart fixture at {source_path}: {exc}") from exc
