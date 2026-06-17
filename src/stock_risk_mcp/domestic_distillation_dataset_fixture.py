from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.domestic_distillation_dataset_models import DomesticDistillationDatasetFixture


def load_domestic_distillation_dataset_fixture(path) -> DomesticDistillationDatasetFixture:
    fixture_path = Path(path)
    try:
        if fixture_path.suffix.lower() != ".json":
            raise ValueError("domestic distillation dataset fixture must be an explicit local JSON file")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return DomesticDistillationDatasetFixture.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"invalid domestic distillation dataset fixture: {exc}") from exc
