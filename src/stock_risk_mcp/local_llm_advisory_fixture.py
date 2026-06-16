import json
from pathlib import Path

from stock_risk_mcp.local_llm_advisory_models import LocalLLMAdvisoryFixture


def load_local_llm_advisory_fixture(path) -> LocalLLMAdvisoryFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("local LLM advisory fixture must be an explicit local JSON file")
        return LocalLLMAdvisoryFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid local LLM advisory fixture: {exc}") from exc
