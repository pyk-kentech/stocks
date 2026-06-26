from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.feature_store_models import (
    FeatureStoreAuditRecord,
    FeatureStoreDatasetProfile,
    FeatureStoreFeatureRow,
    FeatureStoreLeakageReport,
    FeatureStorePriceBar,
    FeatureStoreReadinessStatus,
    FeatureStoreTrainingDatasetManifest,
    FeatureStoreTrainingRow,
    FeatureStoreWalkForwardPlan,
)
from stock_risk_mcp.models import StrictModel


ScalarValue = int | float | str | bool | None


def _aware(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _upper_required(value, field_name: str) -> str:
    return _string_required(value, field_name).upper()


def _normalize_list(value, field_name: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if upper:
        return [_upper_required(item, field_name) for item in value]
    return [_string_required(item, field_name) for item in value]


def _validate_relative_path(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local path")
    path = Path(cleaned)
    if path.is_absolute():
        raise ValueError(f"{field_name} must be relative")
    if ".." in path.parts:
        raise ValueError(f"{field_name} must not contain path traversal")
    return cleaned


def _validate_scalar_map(value: dict[str, Any], field_name: str) -> dict[str, ScalarValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked = ("credential", "token", "secret", "account", "order", "authorization")
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        lowered = name.lower()
        if any(marker in lowered for marker in blocked):
            raise ValueError(f"{field_name} contains blocked field name: {name}")
        if isinstance(raw, bool) or raw is None or isinstance(raw, (int, float, str)):
            normalized[name] = raw
            continue
        raise ValueError(f"{field_name} values must be scalar only")
    return normalized


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "read_only",
        "report_only",
        "non_executable",
        "local_file_only",
        "offline_only",
        "no_network",
        "no_provider_api",
        "no_order",
        "no_account_mutation",
        "no_live_prod",
        "no_autonomous_trading",
        "no_broker_api",
        "no_broker_paper_api",
        "no_kiwoom_api",
        "no_ls_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_env_read",
        "no_credential_read",
        "no_token_loading",
        "no_auth_header_generation",
        "no_model_training",
        "paper_simulated_only",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class PaperEvaluationReadinessStatus(StrEnum):
    PAPER_EVALUATION_READY = "PAPER_EVALUATION_READY"
    PLAN_READY = "PLAN_READY"
    SIGNAL_REPLAY_READY = "SIGNAL_REPLAY_READY"
    FILL_SIMULATION_READY = "FILL_SIMULATION_READY"
    LEDGER_READY = "LEDGER_READY"
    PORTFOLIO_READY = "PORTFOLIO_READY"
    METRICS_READY = "METRICS_READY"
    RISK_REPORT_READY = "RISK_REPORT_READY"
    SPLIT_REPORT_READY = "SPLIT_REPORT_READY"
    REGIME_REPORT_READY = "REGIME_REPORT_READY"
    EVENT_WINDOW_REPORT_READY = "EVENT_WINDOW_REPORT_READY"
    INTEGRATION_READY = "INTEGRATION_READY"
    LABEL_GAP = "LABEL_GAP"
    FILL_GAP = "FILL_GAP"
    COST_MODEL_GAP = "COST_MODEL_GAP"
    DATA_GAP = "DATA_GAP"
    LEAKAGE_BLOCKED = "LEAKAGE_BLOCKED"
    DATA_SNOOPING_GAP = "DATA_SNOOPING_GAP"
    BLOCKED_PROVIDER_CALL = "BLOCKED_PROVIDER_CALL"
    BLOCKED_ACCOUNT_OR_ORDER = "BLOCKED_ACCOUNT_OR_ORDER"
    BLOCKED_EXECUTABLE_OUTPUT = "BLOCKED_EXECUTABLE_OUTPUT"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    REJECTED = "REJECTED"


class PaperEvaluationSignalStatus(StrEnum):
    SIGNAL_READY = "SIGNAL_READY"
    WATCH_ONLY = "WATCH_ONLY"
    NO_TRADE = "NO_TRADE"
    BLOCKED_EVENT_RISK = "BLOCKED_EVENT_RISK"
    BLOCKED_MACRO_RISK = "BLOCKED_MACRO_RISK"
    BLOCKED_LIQUIDITY = "BLOCKED_LIQUIDITY"
    BLOCKED_LEAKAGE = "BLOCKED_LEAKAGE"
    DATA_GAP = "DATA_GAP"
    REJECTED = "REJECTED"


class PaperEvaluationSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"
    NO_TRADE = "NO_TRADE"


class PaperEvaluationFillPolicy(StrEnum):
    NEXT_BAR_OPEN = "NEXT_BAR_OPEN"
    NEXT_BAR_CLOSE = "NEXT_BAR_CLOSE"
    VWAP_APPROX = "VWAP_APPROX"
    LIMIT_TOUCH_SIMULATED = "LIMIT_TOUCH_SIMULATED"
    NO_FILL = "NO_FILL"


class PaperEvaluationFillStatus(StrEnum):
    FILLED = "FILLED"
    NO_FILL = "NO_FILL"
    FILL_GAP = "FILL_GAP"
    LEAKAGE_BLOCKED = "LEAKAGE_BLOCKED"


class PaperEvaluationConfidenceBucket(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PaperEvaluationRiskBucket(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class PaperEvaluationDuplicatePositionPolicy(StrEnum):
    BLOCK = "BLOCK"
    ALLOW_ADD = "ALLOW_ADD"


class PaperEvaluationForcedClosePolicy(StrEnum):
    FORCE_CLOSE_AT_NEXT_AVAILABLE_BAR = "FORCE_CLOSE_AT_NEXT_AVAILABLE_BAR"


class _BaseSafety(StrictModel):
    read_only: bool = True
    report_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_account_mutation: bool = True
    no_live_prod: bool = True
    no_autonomous_trading: bool = True
    no_broker_api: bool = True
    no_broker_paper_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_env_read: bool = True
    no_credential_read: bool = True
    no_token_loading: bool = True
    no_auth_header_generation: bool = True
    no_model_training: bool = True
    paper_simulated_only: bool = True


class PaperEvaluationRuleOverride(StrictModel):
    allow_symbolic_sell: bool = False
    buy_score_threshold: float = Field(default=0.65, ge=0, le=1)
    watch_score_threshold: float = Field(default=0.5, ge=0, le=1)
    liquidity_min_threshold: float = Field(default=0.3, ge=0)
    macro_block_threshold: float = Field(default=0.8, ge=0, le=1)


class PaperEvaluationConfig(StrictModel):
    fill_policy: PaperEvaluationFillPolicy = PaperEvaluationFillPolicy.NEXT_BAR_OPEN
    starting_cash: float = Field(default=10_000_000.0, gt=0)
    commission_bps: float = Field(default=5.0, ge=0)
    tax_bps: float = Field(default=15.0, ge=0)
    slippage_bps: float = Field(default=10.0, ge=0)
    spread_penalty_bps: float = Field(default=5.0, ge=0)
    fx_cost_bps: float = Field(default=0.0, ge=0)
    allow_symbolic_sell: bool = False
    duplicate_position_policy: PaperEvaluationDuplicatePositionPolicy = PaperEvaluationDuplicatePositionPolicy.BLOCK
    forced_close_policy: PaperEvaluationForcedClosePolicy = PaperEvaluationForcedClosePolicy.FORCE_CLOSE_AT_NEXT_AVAILABLE_BAR


class PaperEvaluationPlan(_BaseSafety):
    plan_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    dataset_profile: FeatureStoreDatasetProfile
    labeled_dataset: bool = False
    fill_policy: PaperEvaluationFillPolicy
    split_count: int = Field(default=0, ge=0)
    gating_findings: list[str] = Field(default_factory=list)

    @field_validator("plan_id", "dataset_id", mode="before")
    @classmethod
    def normalize_id(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("gating_findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "gating_findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation plan")


class PaperEvaluationSignal(_BaseSafety):
    signal_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    row_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    split_role: str = Field(..., min_length=1)
    feature_asof: datetime
    signal_status: PaperEvaluationSignalStatus
    side: PaperEvaluationSide
    signal_score: float = Field(default=0.0, ge=0, le=1)
    reason_codes: list[str] = Field(default_factory=list)
    used_feature_keys: list[str] = Field(default_factory=list)
    signal_metadata: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("signal_id", "dataset_id", "row_id", "instrument_id", "split_id", "split_role", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("feature_asof", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("reason_codes", "used_feature_keys", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=info.field_name == "reason_codes")

    @field_validator("signal_metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value):
        return _validate_scalar_map(value or {}, "signal_metadata")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation signal")


class PaperEvaluationIntent(_BaseSafety):
    intent_id: str = Field(..., min_length=1)
    signal_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    row_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    feature_asof: datetime
    side: PaperEvaluationSide
    intent_source: str = Field(..., min_length=1)
    confidence_bucket: PaperEvaluationConfidenceBucket
    risk_bucket: PaperEvaluationRiskBucket
    sizing_hint: float = Field(default=0.0, ge=0)
    stop_hint: float | None = Field(default=None, ge=0)
    take_profit_hint: float | None = Field(default=None, ge=0)
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("intent_id", "signal_id", "dataset_id", "row_id", "instrument_id", "intent_source", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "intent_source":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("feature_asof", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value):
        return _normalize_list(value, "reason_codes", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation intent")


class PaperEvaluationFill(_BaseSafety):
    fill_id: str = Field(..., min_length=1)
    intent_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    side: PaperEvaluationSide
    fill_policy: PaperEvaluationFillPolicy
    fill_status: PaperEvaluationFillStatus
    fill_price: float | None = Field(default=None, gt=0)
    fill_quantity: float = Field(default=0.0, ge=0)
    fill_observed_at: datetime | None = None
    fill_available_at: datetime | None = None
    gross_notional: float = Field(default=0.0, ge=0)
    commission_cost: float = Field(default=0.0, ge=0)
    tax_cost: float = Field(default=0.0, ge=0)
    slippage_cost: float = Field(default=0.0, ge=0)
    spread_penalty_cost: float = Field(default=0.0, ge=0)
    fx_cost: float = Field(default=0.0, ge=0)
    assumption_notes: list[str] = Field(default_factory=list)

    @field_validator("fill_id", "intent_id", "dataset_id", "instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("fill_observed_at", "fill_available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("assumption_notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_list(value, "assumption_notes")

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation fill")


class PaperEvaluationLedgerEntry(_BaseSafety):
    ledger_entry_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    event_time: datetime
    event_type: str = Field(..., min_length=1)
    side: PaperEvaluationSide
    cash_before: float
    cash_after: float
    realized_pnl_delta: float = 0.0
    fees_delta: float = 0.0
    taxes_delta: float = 0.0
    slippage_delta: float = 0.0

    @field_validator("ledger_entry_id", "dataset_id", "split_id", "instrument_id", "event_type", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "event_type":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)

    @field_validator("event_time", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation ledger entry")


class PaperEvaluationPosition(_BaseSafety):
    position_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    open_quantity: float = Field(default=0.0, ge=0)
    average_entry_price: float = Field(default=0.0, ge=0)
    market_price: float = Field(default=0.0, ge=0)
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    closed: bool = False

    @field_validator("position_id", "dataset_id", "split_id", "instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation position")


class PaperEvaluationPortfolioSnapshot(_BaseSafety):
    snapshot_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    observed_at: datetime
    cash: float
    equity: float
    gross_exposure: float = Field(default=0.0, ge=0)
    net_exposure: float = 0.0
    drawdown_amount: float = Field(default=0.0, ge=0)
    drawdown_pct: float = Field(default=0.0, ge=0)
    open_position_count: int = Field(default=0, ge=0)

    @field_validator("snapshot_id", "dataset_id", "split_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation portfolio snapshot")


class PaperEvaluationTrade(_BaseSafety):
    trade_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    side: PaperEvaluationSide
    entry_time: datetime
    exit_time: datetime | None = None
    entry_price: float = Field(..., gt=0)
    exit_price: float | None = Field(default=None, gt=0)
    quantity: float = Field(..., gt=0)
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    holding_bars: int = Field(default=0, ge=0)
    forced_close: bool = False
    split_role: str = Field(..., min_length=1)
    regime_label: str = Field(default="UNKNOWN", min_length=1)
    event_window_label: str = Field(default="OUTSIDE_EVENT_WINDOW", min_length=1)
    liquidity_bucket: str = Field(default="UNKNOWN", min_length=1)

    @field_validator("trade_id", "dataset_id", "split_id", "instrument_id", "split_role", "regime_label", "event_window_label", "liquidity_bucket", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "liquidity_bucket":
            return _string_required(value, info.field_name).upper()
        return _upper_required(value, info.field_name)

    @field_validator("entry_time", "exit_time", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation trade")


class PaperEvaluationEquityCurve(_BaseSafety):
    curve_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    points: list[PaperEvaluationPortfolioSnapshot] = Field(default_factory=list)

    @field_validator("curve_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation equity curve")


class PaperEvaluationMetricsReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    trade_count: int = Field(default=0, ge=0)
    win_rate: float | None = Field(default=None, ge=0, le=1)
    average_return: float | None = None
    median_return: float | None = None
    gross_return: float | None = None
    net_return: float | None = None
    profit_factor: float | None = None
    fill_rate: float | None = Field(default=None, ge=0, le=1)
    blocked_signal_count: int = Field(default=0, ge=0)
    gap_count: int = Field(default=0, ge=0)
    label_dependent_metrics_available: bool = True

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation metrics report")


class PaperEvaluationRiskReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    max_drawdown: float = Field(default=0.0, ge=0)
    volatility: float | None = Field(default=None, ge=0)
    sharpe_like_ratio: float | None = None
    exposure_time: float = Field(default=0.0, ge=0)
    turnover: float = Field(default=0.0, ge=0)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation risk report")


class PaperEvaluationSplitReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    split_metrics: dict[str, dict[str, float | int | str | None]] = Field(default_factory=dict)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation split report")


class PaperEvaluationRegimeReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    regime_metrics: dict[str, dict[str, float | int | str | None]] = Field(default_factory=dict)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation regime report")


class PaperEvaluationEventWindowReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    event_window_metrics: dict[str, dict[str, float | int | str | None]] = Field(default_factory=dict)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation event window report")


class PaperEvaluationIntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    v10_manifest_integration_ready: bool = False
    v10_split_integration_ready: bool = False
    v10_leakage_gate_passed: bool = False
    v8_feature_context_ready: bool = False
    v9_macro_context_ready: bool = False
    v710_position_sizing_context_ready: bool = False
    v711_event_risk_context_ready: bool = False
    v712_outlier_context_ready: bool = False
    v713_mock_rehearsal_context_ready: bool = False

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation integration report")


class PaperEvaluationSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation safety report")


class PaperEvaluationGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return _string_required(value, "message")


class PaperEvaluationGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: PaperEvaluationReadinessStatus
    gap_entries: list[PaperEvaluationGapEntry] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_model(self):
        return _validate_safety_flags(self, "paper evaluation gap report")


class PaperEvaluationPipelineInput(_BaseSafety):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    schema_version: str = Field(default="V11.0", min_length=1)
    generator_version: str = Field(default="V11.0", min_length=1)
    training_dataset_manifest: FeatureStoreTrainingDatasetManifest
    feature_rows: list[FeatureStoreFeatureRow] = Field(default_factory=list)
    training_rows: list[FeatureStoreTrainingRow] = Field(default_factory=list)
    walk_forward_plan: FeatureStoreWalkForwardPlan
    leakage_report: FeatureStoreLeakageReport
    price_history_rows: list[FeatureStorePriceBar] = Field(default_factory=list)
    config: PaperEvaluationConfig = Field(default_factory=PaperEvaluationConfig)
    rule_override: PaperEvaluationRuleOverride | None = None
    local_dataset_paths: list[str] = Field(default_factory=list)
    audit_records: list[FeatureStoreAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", "dataset_id", "schema_version", "generator_version", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("local_dataset_paths", mode="before")
    @classmethod
    def normalize_paths(cls, value):
        paths = _normalize_list(value, "local_dataset_paths")
        return [_validate_relative_path(path, "local_dataset_paths") or "" for path in paths]

    @model_validator(mode="after")
    def validate_input(self):
        if self.training_dataset_manifest.dataset_id != self.dataset_id:
            raise ValueError("training dataset manifest dataset_id must match paper evaluation dataset_id")
        return _validate_safety_flags(self, "paper evaluation pipeline input")


class PaperEvaluationPipelineResult(StrictModel):
    plan: PaperEvaluationPlan
    signals: list[PaperEvaluationSignal]
    intents: list[PaperEvaluationIntent]
    fills: list[PaperEvaluationFill]
    ledger_entries: list[PaperEvaluationLedgerEntry]
    positions: list[PaperEvaluationPosition]
    portfolio_snapshots: list[PaperEvaluationPortfolioSnapshot]
    trades: list[PaperEvaluationTrade]
    equity_curve: PaperEvaluationEquityCurve
    metrics_report: PaperEvaluationMetricsReport
    risk_report: PaperEvaluationRiskReport
    split_report: PaperEvaluationSplitReport
    regime_report: PaperEvaluationRegimeReport
    event_window_report: PaperEvaluationEventWindowReport
    integration_report: PaperEvaluationIntegrationReport
    safety_report: PaperEvaluationSafetyReport
    gap_report: PaperEvaluationGapReport
