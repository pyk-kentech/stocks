from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.offline_prompt_pack_models import PromptPack


def load_offline_prompt_pack_fixture(path) -> PromptPack:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("offline prompt pack fixture must be an explicit local JSON file")
        return PromptPack.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid offline prompt pack fixture: {exc}") from exc
