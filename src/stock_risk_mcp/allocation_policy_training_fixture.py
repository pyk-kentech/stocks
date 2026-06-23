from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.allocation_policy_training_models import AllocationPolicyCandidateInput


def load_allocation_policy_training_fixture(path) -> AllocationPolicyCandidateInput:
    source_path = str(path)
    fixture_path = Path(path)
    try:
        lowered = source_path.strip().lower()
        if "://" in lowered or lowered.startswith("//"):
            raise ValueError("allocation policy training fixture must be a local file path")
        if lowered.endswith(".parquet"):
            raise ValueError("parquet remains unsupported")
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("allocation policy training fixture must be an explicit local JSON file")
        return AllocationPolicyCandidateInput.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid allocation policy training fixture at {source_path}: {exc}") from exc
