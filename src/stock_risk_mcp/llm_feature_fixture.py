import json
from pathlib import Path

from stock_risk_mcp.llm_feature_models import LLMOutcomeFixture, LLMSignalFixture


def load_llm_signal_fixture(path) -> LLMSignalFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("LLM signal fixture must be an explicit local JSON file")
        return LLMSignalFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid LLM signal fixture: {exc}") from exc


def load_llm_outcome_fixture(path) -> LLMOutcomeFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("LLM outcome fixture must be an explicit local JSON file")
        return LLMOutcomeFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid LLM outcome fixture: {exc}") from exc
