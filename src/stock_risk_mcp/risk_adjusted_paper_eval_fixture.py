from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.risk_adjusted_paper_eval_models import RiskAdjustedPaperEvalInput


def load_risk_adjusted_paper_eval_fixture(path) -> RiskAdjustedPaperEvalInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("risk-adjusted paper evaluation fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("risk-adjusted paper evaluation fixture must be an explicit local JSON file")
        return RiskAdjustedPaperEvalInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid risk-adjusted paper evaluation fixture at {source_path}: {exc}") from exc
