import json
from pathlib import Path

from stock_risk_mcp.walk_forward_policy_models import WalkForwardPolicyFixture


def load_walk_forward_policy_fixture(path) -> WalkForwardPolicyFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("policy replay fixture must be an explicit local JSON file")
        return WalkForwardPolicyFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
    except Exception as exc:
        raise ValueError(f"invalid policy replay fixture: {exc}") from exc
