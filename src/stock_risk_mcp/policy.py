from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from stock_risk_mcp.models import RiskPolicy


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "policies" / "default_policy.yaml"


def load_policy(path: str | Path | None = None) -> RiskPolicy:
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    if not policy_path.exists():
        raise FileNotFoundError(f"Risk policy file not found: {policy_path}")

    with policy_path.open("r", encoding="utf-8") as file:
        raw_policy: Any = yaml.safe_load(file)

    if not isinstance(raw_policy, dict):
        raise ValueError(f"Risk policy YAML must contain a mapping: {policy_path}")

    return RiskPolicy.model_validate(raw_policy)
