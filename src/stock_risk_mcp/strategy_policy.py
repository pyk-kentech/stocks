from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import model_validator

from stock_risk_mcp.models import StrictModel


class StrategyPolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    BACKTESTED = "BACKTESTED"
    PAPER_TRADING = "PAPER_TRADING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class StrategyPolicyCreator(StrEnum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    LLM = "LLM"
    OPTIMIZER = "OPTIMIZER"


FORBIDDEN_HARD_RISK_KEYS = {
    "block_nasdaq_noncompliant",
    "block_dilution_high",
    "block_unknown_dilution",
    "allow_market_order",
    "allow_margin",
    "allow_options",
    "allow_disable_stop_loss",
    "max_daily_loss_pct",
    "max_single_position_pct",
    "min_cash_pct",
}

DEFAULT_WEIGHTS = {
    "return_5d_score": 0.08,
    "return_20d_score": 0.06,
    "sma_alignment_score": 0.08,
    "rsi_score": 0.06,
    "volume_spike_score": 0.12,
    "dollar_volume_score": 0.12,
    "volatility_penalty": 0.10,
    "max_drawdown_penalty": 0.08,
    "bollinger_position_score": 0.05,
    "setup_grade_score": 0.15,
    "risk_reward_score": 0.10,
}
DEFAULT_SETUP_THRESHOLDS = {"A": 80.0, "B": 60.0, "C": 40.0, "NO_TRADE": 0.0}
DEFAULT_BASKET_RULES: dict[str, float | int | bool] = {
    "max_candidates": 10,
    "min_candidates": 3,
    "max_same_sector_count": 3,
    "max_same_theme_count": 3,
    "allow_review_candidates": True,
    "allow_c_setup": False,
}
DEFAULT_RISK_OVERRIDES: dict[str, float | int | bool] = {
    "A_risk_unit": 1.0,
    "B_risk_unit": 0.5,
    "C_risk_unit": 0.0,
    "max_basket_loss_pct": 1.0,
    "max_basket_notional_pct": 25.0,
    "max_single_candidate_loss_pct": 0.25,
}


class StrategyPolicy(StrictModel):
    policy_id: str
    version: str
    status: StrategyPolicyStatus
    weights: dict[str, float]
    setup_thresholds: dict[str, float]
    basket_rules: dict[str, float | int | bool]
    risk_overrides: dict[str, float | int | bool]
    created_by: StrategyPolicyCreator
    reason: str
    parent_policy_id: str | None = None
    parent_version: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_policy(self) -> "StrategyPolicy":
        return validate_strategy_policy(self)


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights must be non-negative")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("weights sum must be greater than zero")
    return {key: value / total for key, value in weights.items()}


def validate_strategy_policy(policy: StrategyPolicy) -> StrategyPolicy:
    if any(value < 0 for value in policy.weights.values()):
        raise ValueError("weights must be non-negative")
    total = sum(policy.weights.values())
    if not 0.95 <= total <= 1.05:
        raise ValueError("weights sum must be between 0.95 and 1.05")
    thresholds = policy.setup_thresholds
    try:
        ordered = thresholds["A"] > thresholds["B"] > thresholds["C"] >= thresholds["NO_TRADE"]
    except KeyError as error:
        raise ValueError(f"missing setup threshold: {error.args[0]}") from error
    if not ordered:
        raise ValueError("setup thresholds must follow A > B > C >= NO_TRADE")
    forbidden = FORBIDDEN_HARD_RISK_KEYS.intersection(policy.risk_overrides)
    if forbidden:
        raise ValueError(f"forbidden hard risk override keys: {sorted(forbidden)}")
    basket_loss = float(policy.risk_overrides.get("max_basket_loss_pct", 1.0))
    if not 0 < basket_loss <= 5:
        raise ValueError("max_basket_loss_pct must be greater than 0 and at most 5")
    candidate_loss = float(policy.risk_overrides.get("max_single_candidate_loss_pct", 0.25))
    if not 0 < candidate_loss <= 1:
        raise ValueError("max_single_candidate_loss_pct must be greater than 0 and at most 1")
    return policy


def create_default_strategy_policy() -> StrategyPolicy:
    return StrategyPolicy(
        policy_id="default",
        version="v1",
        status=StrategyPolicyStatus.ACTIVE,
        weights=DEFAULT_WEIGHTS.copy(),
        setup_thresholds=DEFAULT_SETUP_THRESHOLDS.copy(),
        basket_rules=DEFAULT_BASKET_RULES.copy(),
        risk_overrides=DEFAULT_RISK_OVERRIDES.copy(),
        created_by=StrategyPolicyCreator.SYSTEM,
        reason="Default adaptive strategy policy",
        created_at=datetime.now(),
    )
