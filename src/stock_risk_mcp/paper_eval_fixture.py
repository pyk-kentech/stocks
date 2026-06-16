import json
from pathlib import Path

from stock_risk_mcp.paper_eval_models import PaperEvalFixture


def load_paper_eval_fixture(path) -> PaperEvalFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("paper evaluation fixture must be an explicit local JSON file")
        return PaperEvalFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid paper evaluation fixture: {exc}") from exc
