from __future__ import annotations

import math
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.paper_eval_models import PaperPriceBar


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def reject_bool(value):
    if isinstance(value, bool):
        raise ValueError("numeric value must not be boolean")
    return value


POLICY_REPLAY_METADATA = {
    "advisory_only": True,
    "production_policy_changed": False,
    "orders_created": False,
    "order_intents_created": False,
    "execution_approved": False,
    "gates_bypassed": False,
    "external_network_calls": False,
}


class ScoreWeights(StrictModel):
    technical: float = Field(..., ge=0, allow_inf_nan=False)
    discovery: float = Field(..., ge=0, allow_inf_nan=False)
    llm: float = Field(..., ge=0, allow_inf_nan=False)

    @field_validator("technical", "discovery", "llm", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)


class ReplayPolicyConfig(StrictModel):
    policy_id: str = Field(..., min_length=1)
    score_weights: ScoreWeights
    minimum_score_threshold: float = Field(..., ge=0, allow_inf_nan=False)
    minimum_risk_reward: float = Field(..., gt=0, allow_inf_nan=False)
    allowed_setup_grades: list[str] = Field(..., min_length=1)
    max_risk_pct_per_trade: float = Field(..., gt=0, le=1, allow_inf_nan=False)
    max_basket_risk_pct: float = Field(..., gt=0, le=1, allow_inf_nan=False)
    llm_weight_cap: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    allow_short: bool = False
    allow_margin: bool = False
    allow_leverage: bool = False
    allow_market_orders: bool = False

    @field_validator("minimum_score_threshold", "minimum_risk_reward", "max_risk_pct_per_trade", "max_basket_risk_pct", "llm_weight_cap", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)

    @field_validator("policy_id")
    @classmethod
    def normalize_policy_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("allowed_setup_grades")
    @classmethod
    def normalize_grades(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().upper() for value in values})
        if any(not value for value in normalized):
            raise ValueError("allowed_setup_grades must not contain blank values")
        return normalized


class WalkForwardWindowConfig(StrictModel):
    train_window_count: int = Field(..., ge=1)
    eval_window_count: int = Field(..., ge=1)
    window_stride: int = Field(..., ge=1)
    minimum_eval_trades: int = Field(..., ge=0)


class PolicyPromotionGates(StrictModel):
    minimum_sample_count: int = Field(..., ge=0)
    max_drawdown_pct_cap: float = Field(..., ge=0, allow_inf_nan=False)
    minimum_return_improvement_pct: float = Field(..., allow_inf_nan=False)
    minimum_stability_score: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    max_missing_data_rate: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    max_blocked_rate: float = Field(..., ge=0, le=1, allow_inf_nan=False)

    @field_validator("max_drawdown_pct_cap", "minimum_return_improvement_pct", "minimum_stability_score", "max_missing_data_rate", "max_blocked_rate", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)


class ReplayRow(StrictModel):
    ticker: str = Field(..., min_length=1)
    timestamp: datetime
    setup_grade: str = Field(..., min_length=1)
    technical_score: float = Field(..., ge=0, allow_inf_nan=False)
    discovery_score: float = Field(..., ge=0, allow_inf_nan=False)
    llm_score: float = Field(..., ge=0, allow_inf_nan=False)
    entry_reference: float = Field(..., gt=0, allow_inf_nan=False)
    stop_reference: float = Field(..., gt=0, allow_inf_nan=False)
    target_reference: float = Field(..., gt=0, allow_inf_nan=False)
    price_path_id: str = Field(..., min_length=1)
    _timestamp = field_validator("timestamp")(aware)

    @field_validator("technical_score", "discovery_score", "llm_score", "entry_reference", "stop_reference", "target_reference", mode="before")
    @classmethod
    def numeric_only(cls, value):
        return reject_bool(value)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("setup_grade")
    @classmethod
    def normalize_grade(cls, value: str) -> str:
        return value.strip().upper()


class ReplayPricePath(StrictModel):
    price_path_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    bars: list[PaperPriceBar] = Field(..., min_length=1)

    @field_validator("price_path_id")
    @classmethod
    def normalize_path_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_bars(self):
        timestamps = [bar.timestamp for bar in self.bars]
        if timestamps != sorted(timestamps):
            raise ValueError("bars must be ordered")
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("duplicate bar timestamp")
        return self


class WalkForwardPolicyFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    window_config: WalkForwardWindowConfig
    promotion_gates: PolicyPromotionGates
    baseline_policy: ReplayPolicyConfig
    candidate_policies: list[ReplayPolicyConfig] = Field(..., min_length=1)
    replay_rows: list[ReplayRow] = Field(..., min_length=1)
    price_paths: list[ReplayPricePath] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "3.7-policy-replay-fixture":
            raise ValueError("schema_version must be exactly 3.7-policy-replay-fixture")
        return value

    @model_validator(mode="after")
    def validate_links(self):
        candidate_ids = [policy.policy_id for policy in self.candidate_policies]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate policy_id values must be unique")
        if self.baseline_policy.policy_id in candidate_ids:
            raise ValueError("candidate policy_id may not equal baseline policy_id")
        path_ids = {path.price_path_id: path for path in self.price_paths}
        for row in self.replay_rows:
            if row.price_path_id not in path_ids:
                raise ValueError("replay row references missing price_path_id")
            if row.ticker != path_ids[row.price_path_id].ticker:
                raise ValueError("replay row ticker must match linked price path ticker")
        return self


class WalkForwardWindow(StrictModel):
    train_window_dates: list[str]
    eval_window_dates: list[str]
    train_rows: list[ReplayRow]
    eval_rows: list[ReplayRow]


class PolicyWindowMetrics(StrictModel):
    policy_id: str
    train_window_dates: list[str]
    eval_window_dates: list[str]
    replay_row_count: int
    total_return_pct: float = 0
    max_drawdown_pct: float = 0
    win_rate: float | None = None
    profit_factor: float | None = None
    expectancy_amount: float | None = None
    exposure_time_pct: float = 0
    trade_count: int = 0
    missing_data_rate: float = 0
    blocked_rate: float = 0
    missing_data_count: int = 0
    blocked_count: int = 0
    safety_violation: bool = False


class WindowPolicyComparison(StrictModel):
    policy_id: str
    eval_window_dates: list[str]
    baseline_total_return_pct: float
    candidate_total_return_pct: float
    return_delta_pct: float
    baseline_trade_count: int
    candidate_trade_count: int


class WindowReplayResult(StrictModel):
    train_window_dates: list[str]
    eval_window_dates: list[str]
    baseline: PolicyWindowMetrics
    candidate_results: list[PolicyWindowMetrics]


class CandidatePolicyComparison(StrictModel):
    policy_id: str
    window_comparisons: list[WindowPolicyComparison]
    aggregate_baseline_metrics: PolicyWindowMetrics
    aggregate_candidate_metrics: PolicyWindowMetrics
    aggregate_return_delta_pct: float
    stability_score: float
    promotion_decision: str
    gate_reasons: list[str] = Field(default_factory=list)


class WalkForwardPolicyReport(StrictModel):
    schema_version: str = "3.7-policy-replay-report"
    fixture_checksum: str
    run_id: str
    created_at: datetime
    baseline_policy: ReplayPolicyConfig
    candidate_policies: list[ReplayPolicyConfig]
    window_results: list[WindowReplayResult]
    candidate_comparisons: list[CandidatePolicyComparison]
    metadata_json: dict = Field(default_factory=lambda: dict(POLICY_REPLAY_METADATA))
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_report_schema(cls, value: str) -> str:
        if value != "3.7-policy-replay-report":
            raise ValueError("schema_version must be exactly 3.7-policy-replay-report")
        return value

    @model_validator(mode="after")
    def finite_metrics(self):
        for comparison in self.candidate_comparisons:
            if not math.isfinite(comparison.aggregate_return_delta_pct):
                raise ValueError("aggregate_return_delta_pct must be finite")
        return self
