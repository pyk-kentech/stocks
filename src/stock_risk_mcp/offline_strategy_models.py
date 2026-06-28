from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_market_data_models import HistoricalOhlcvDatasetManifest, HistoricalOhlcvRow
from stock_risk_mcp.models import StrictModel


class StrEnum(str, Enum):
    pass


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
    path = Path(cleaned)
    if "://" in cleaned.lower() or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a safe relative local path")
    return cleaned


def _validate_scalar_map(value: dict[str, Any], field_name: str) -> dict[str, ScalarValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked = ("credential", "token", "secret", "authorization", "account", "order", "broker")
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        if any(marker in name.lower() for marker in blocked):
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
        "simulated_only",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class OfflineStrategyStatus(StrEnum):
    READY = "READY"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    WATCHLIST_ONLY = "WATCHLIST_ONLY"
    WATCHLIST_ONLY_ROLLING_ONLY = "WATCHLIST_ONLY_ROLLING_ONLY"
    BLOCKED = "BLOCKED"
    PROMOTED_OFFLINE_CANDIDATE = "PROMOTED_OFFLINE_CANDIDATE"
    REJECTED = "REJECTED"


class OfflineStrategyFamily(StrEnum):
    VOLUME_PULLBACK_LONG = "VOLUME_PULLBACK_LONG"
    UPPER_WICK_REVERSAL = "UPPER_WICK_REVERSAL"
    RSI_OVERSOLD_REBOUND = "RSI_OVERSOLD_REBOUND"
    MACD_RSI_MOMENTUM = "MACD_RSI_MOMENTUM"


class OfflineStrategyTemplateId(StrEnum):
    VOLUME_PULLBACK_LONG_V1 = "VOLUME_PULLBACK_LONG_V1"
    UPPER_WICK_REVERSAL_V1 = "UPPER_WICK_REVERSAL_V1"
    RSI_OVERSOLD_REBOUND_V1 = "RSI_OVERSOLD_REBOUND_V1"
    MACD_RSI_MOMENTUM_V1 = "MACD_RSI_MOMENTUM_V1"


class OfflineStrategyDataRequirement(StrEnum):
    DAILY_OHLCV = "DAILY_OHLCV"
    INTRADAY_OHLCV = "INTRADAY_OHLCV"
    HIGH_LOW_REQUIRED = "HIGH_LOW_REQUIRED"
    VOLUME_REQUIRED = "VOLUME_REQUIRED"
    DIVERGENCE_CONTEXT_REQUIRED = "DIVERGENCE_CONTEXT_REQUIRED"


class OfflineStrategySupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"


class OfflineStrategyDirection(StrEnum):
    LONG_ONLY = "LONG_ONLY"
    SHORT_RESEARCH_ONLY = "SHORT_RESEARCH_ONLY"
    AVOID_LONG_ONLY = "AVOID_LONG_ONLY"


class OfflineStrategySignalAction(StrEnum):
    ENTER_LONG = "ENTER_LONG"
    EXIT_LONG = "EXIT_LONG"
    HOLD = "HOLD"
    AVOID_LONG = "AVOID_LONG"
    RISK_WARNING = "RISK_WARNING"


class OfflineStrategyExitReason(StrEnum):
    STOP_HIT = "STOP_HIT"
    TARGET_HIT = "TARGET_HIT"
    TIME_EXIT = "TIME_EXIT"
    MACD_DEAD_CROSS = "MACD_DEAD_CROSS"
    RSI_50_LOSS = "RSI_50_LOSS"
    BREAKEVEN_STOP = "BREAKEVEN_STOP"
    DATA_GAP = "DATA_GAP"


class OfflineStrategyRiskModel(StrEnum):
    FIXED_R = "FIXED_R"
    ATR_STOP = "ATR_STOP"
    NEAREST_SWING_LOW = "NEAREST_SWING_LOW"
    WICK_HIGH_BUFFER = "WICK_HIGH_BUFFER"
    TIME_BASED_ONLY = "TIME_BASED_ONLY"


class OfflineStrategyAssetLiquidityProfile(StrEnum):
    LARGE_CAP = "LARGE_CAP"
    MID_CAP = "MID_CAP"
    SMALL_CAP = "SMALL_CAP"
    ETF = "ETF"
    HIGH_VOLATILITY_MOMENTUM = "HIGH_VOLATILITY_MOMENTUM"
    LOW_LIQUIDITY_WARNING = "LOW_LIQUIDITY_WARNING"


class OfflineStrategyWalkForwardMode(StrEnum):
    ANCHORED_CHRONOLOGICAL_WALK_FORWARD = "ANCHORED_CHRONOLOGICAL_WALK_FORWARD"
    ROLLING_CHRONOLOGICAL_WALK_FORWARD = "ROLLING_CHRONOLOGICAL_WALK_FORWARD"


class OfflineStrategyReadinessStatus(StrEnum):
    TEMPLATE_CATALOG_READY = "TEMPLATE_CATALOG_READY"
    DATASET_COMPATIBILITY_READY = "DATASET_COMPATIBILITY_READY"
    TRAINING_PLAN_READY = "TRAINING_PLAN_READY"
    WALK_FORWARD_ANCHORED_READY = "WALK_FORWARD_ANCHORED_READY"
    WALK_FORWARD_ROLLING_RESEARCH_ONLY = "WALK_FORWARD_ROLLING_RESEARCH_ONLY"
    BACKTEST_READY = "BACKTEST_READY"
    METRIC_READY = "METRIC_READY"
    PROMOTION_GATE_READY = "PROMOTION_GATE_READY"
    ARTIFACT_READY = "ARTIFACT_READY"
    BLOCKED_NON_CHRONOLOGICAL_SPLIT = "BLOCKED_NON_CHRONOLOGICAL_SPLIT"
    BLOCKED_LEAKAGE_RISK = "BLOCKED_LEAKAGE_RISK"
    WATCHLIST_ONLY_ROLLING_ONLY = "WATCHLIST_ONLY_ROLLING_ONLY"
    DATA_GAP = "DATA_GAP"
    CONFLICT = "CONFLICT"
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"


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
    simulated_only: bool = True


class OfflineStrategyParameter(StrictModel):
    parameter_name: str = Field(..., min_length=1)
    dtype: str = Field(..., min_length=1)
    candidate_values: list[ScalarValue] = Field(default_factory=list)
    default_value: ScalarValue = None

    @field_validator("parameter_name", "dtype", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class OfflineStrategyParameterSpace(StrictModel):
    space_id: str = Field(..., min_length=1)
    template_id: OfflineStrategyTemplateId
    parameters: list[OfflineStrategyParameter] = Field(default_factory=list)
    max_parameter_combinations: int = Field(default=64, ge=1, le=512)

    @field_validator("space_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "space_id")


class OfflineStrategyTemplate(StrictModel):
    template_id: OfflineStrategyTemplateId
    family: OfflineStrategyFamily
    direction: OfflineStrategyDirection
    promotion_eligible: bool = True
    supported_intervals: list[str] = Field(default_factory=list)
    data_requirements: list[OfflineStrategyDataRequirement] = Field(default_factory=list)
    parameter_space: OfflineStrategyParameterSpace

    @field_validator("supported_intervals", mode="before")
    @classmethod
    def normalize_intervals(cls, value):
        return _normalize_list(value, "supported_intervals", upper=True)


class OfflineStrategyCandidate(StrictModel):
    candidate_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    template_id: OfflineStrategyTemplateId
    family: OfflineStrategyFamily
    direction: OfflineStrategyDirection
    promotion_eligible: bool = True
    parameter_set_id: str | None = None
    parameter_summary: str | None = None
    parameter_values: dict[str, ScalarValue] = Field(default_factory=dict)
    asset_liquidity_profile: OfflineStrategyAssetLiquidityProfile = OfflineStrategyAssetLiquidityProfile.LARGE_CAP

    @field_validator("candidate_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("parameter_set_id", mode="before")
    @classmethod
    def normalize_parameter_set_id(cls, value):
        if value is None:
            return None
        return _upper_required(value, "parameter_set_id")

    @field_validator("parameter_summary", mode="before")
    @classmethod
    def normalize_summary(cls, value):
        if value is None:
            return None
        return _string_required(value, "parameter_summary")

    @field_validator("parameter_values", mode="before")
    @classmethod
    def normalize_map(cls, value):
        return _validate_scalar_map(value or {}, "parameter_values")

    @model_validator(mode="after")
    def finalize_parameter_metadata(self):
        if not self.parameter_set_id:
            self.parameter_set_id = f"{self.template_id.value}-P001"
        if not self.parameter_summary:
            self.parameter_summary = ",".join(f"{key}={self.parameter_values[key]}" for key in sorted(self.parameter_values)) or "DEFAULT"
        return self


class OfflineStrategySignal(_BaseSafety):
    signal_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    observed_at: datetime
    action: OfflineStrategySignalAction
    rationale: str = Field(..., min_length=1)
    signal_features: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("signal_id", "candidate_id", "instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("signal_features", mode="before")
    @classmethod
    def normalize_features(cls, value):
        return _validate_scalar_map(value or {}, "signal_features")

    @model_validator(mode="after")
    def validate_signal(self):
        return _validate_safety_flags(self, "signal")


class OfflineStrategyTradeIntent(_BaseSafety):
    intent_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    signal_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    action: OfflineStrategySignalAction
    entry_after_at: datetime
    stop_reference: float | None = None
    target_reference: float | None = None

    @field_validator("intent_id", "candidate_id", "signal_id", "instrument_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("entry_after_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_intent(self):
        return _validate_safety_flags(self, "trade intent")


class OfflineStrategySimulatedTrade(_BaseSafety):
    trade_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    entry_at: datetime
    exit_at: datetime
    entry_price: float = Field(..., gt=0)
    exit_price: float = Field(..., gt=0)
    gross_return: float
    net_return: float
    exit_reason: OfflineStrategyExitReason
    split_role: str = Field(..., min_length=1)

    @field_validator("trade_id", "candidate_id", "instrument_id", "split_role", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("entry_at", "exit_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_trade(self):
        return _validate_safety_flags(self, "simulated trade")


class OfflineStrategyBacktestResult(_BaseSafety):
    result_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    readiness_status: OfflineStrategyReadinessStatus
    trade_count: int = Field(default=0, ge=0)
    cumulative_return: float = 0.0
    max_drawdown: float = 0.0
    trades: list[OfflineStrategySimulatedTrade] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("result_id", "candidate_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warn(cls, value):
        return _normalize_list(value, "warnings", upper=True)

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "backtest result")


class OfflineStrategyMetricSummary(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    trade_count: int = Field(default=0, ge=0)
    out_of_sample_trade_count: int = Field(default=0, ge=0)
    cumulative_return: float = 0.0
    average_trade_return: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    stop_hit_rate: float = 0.0
    exposure: float = 0.0
    turnover: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "candidate_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, value):
        return _normalize_list(value, "warnings", upper=True)

    @model_validator(mode="after")
    def validate_metrics(self):
        return _validate_safety_flags(self, "metric summary")


class OfflineStrategyWalkForwardSplit(StrictModel):
    split_id: str = Field(..., min_length=1)
    split_role: str = Field(..., min_length=1)
    walk_forward_mode: OfflineStrategyWalkForwardMode
    start_at: datetime | None = None
    end_at: datetime | None = None
    row_ids: list[str] = Field(default_factory=list)
    purge_window_count: int = Field(default=0, ge=0)
    embargo_window_count: int = Field(default=0, ge=0)

    @field_validator("split_id", "split_role", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("row_ids", mode="before")
    @classmethod
    def normalize_rows(cls, value):
        return _normalize_list(value, "row_ids", upper=True)


class OfflineStrategyWalkForwardResult(_BaseSafety):
    result_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    primary_mode: OfflineStrategyWalkForwardMode
    readiness_status: OfflineStrategyReadinessStatus
    splits: list[OfflineStrategyWalkForwardSplit] = Field(default_factory=list)
    rolling_secondary_only: bool = False

    @field_validator("result_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "walk forward result")


class OfflineStrategyPromotionGateConfig(StrictModel):
    min_trade_count: int = Field(default=3, ge=1)
    min_walk_forward_folds: int = Field(default=3, ge=1)
    min_out_of_sample_trades: int = Field(default=2, ge=0)
    max_drawdown_cap: float = Field(default=0.15, ge=0)
    min_profit_factor: float = Field(default=1.05, ge=0)
    min_expectancy: float = Field(default=0.0)
    min_average_trade_return: float | None = None


class OfflineStrategyPromotionDecision(_BaseSafety):
    decision_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    family: OfflineStrategyFamily
    status: OfflineStrategyStatus
    reasons: list[str] = Field(default_factory=list)
    diagnostics: dict[str, ScalarValue] = Field(default_factory=dict)

    @field_validator("decision_id", "candidate_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value):
        return _normalize_list(value, "reasons", upper=True)

    @field_validator("diagnostics", mode="before")
    @classmethod
    def normalize_diagnostics(cls, value):
        return _validate_scalar_map(value or {}, "diagnostics")

    @model_validator(mode="after")
    def validate_decision(self):
        return _validate_safety_flags(self, "promotion decision")


class OfflineStrategyDatasetCompatibilityReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: OfflineStrategyReadinessStatus
    support_status: OfflineStrategySupportStatus
    findings: list[str] = Field(default_factory=list)
    row_count: int = Field(default=0, ge=0)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "dataset compatibility report")


class OfflineStrategyTrainingLaunchPlan(_BaseSafety):
    plan_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: OfflineStrategyReadinessStatus
    candidate_count: int = Field(default=0, ge=0)
    primary_walk_forward_mode: OfflineStrategyWalkForwardMode
    rolling_enabled: bool = False

    @field_validator("plan_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_plan(self):
        return _validate_safety_flags(self, "training launch plan")


class OfflineStrategyArtifactManifest(_BaseSafety):
    manifest_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    relative_paths: list[str] = Field(default_factory=list)
    readiness_status: OfflineStrategyReadinessStatus

    @field_validator("manifest_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("relative_paths", mode="before")
    @classmethod
    def normalize_paths(cls, value):
        return [_validate_relative_path(item, "relative_paths") or "" for item in (value or [])]

    @model_validator(mode="after")
    def validate_manifest(self):
        return _validate_safety_flags(self, "artifact manifest")


class OfflineStrategySafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: OfflineStrategyReadinessStatus
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "safety report")


class OfflineStrategyGapEntry(StrictModel):
    gap_id: str = Field(..., min_length=1)
    gap_category: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

    @field_validator("gap_id", "gap_category", "severity", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class OfflineStrategyGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    readiness_status: OfflineStrategyReadinessStatus
    gap_entries: list[OfflineStrategyGapEntry] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "gap report")


class OfflineStrategyPipelineInput(StrictModel):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    manifest: HistoricalOhlcvDatasetManifest | None = None
    ohlcv_rows: list[HistoricalOhlcvRow] = Field(default_factory=list)
    primary_walk_forward_mode: OfflineStrategyWalkForwardMode = OfflineStrategyWalkForwardMode.ANCHORED_CHRONOLOGICAL_WALK_FORWARD
    rolling_enabled: bool = False
    asset_liquidity_profile: OfflineStrategyAssetLiquidityProfile = OfflineStrategyAssetLiquidityProfile.LARGE_CAP
    fee_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=10.0, ge=0)
    search_mode: str = "BOUNDED_GRID"
    promotion_gate_config: OfflineStrategyPromotionGateConfig = Field(default_factory=OfflineStrategyPromotionGateConfig)
    requested_template_ids: list[OfflineStrategyTemplateId] = Field(default_factory=list)

    @field_validator("pipeline_id", "dataset_id", "search_mode", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("requested_template_ids", mode="before")
    @classmethod
    def normalize_templates(cls, value):
        if value is None:
            return []
        return value

    @model_validator(mode="after")
    def validate_input(self):
        if self.manifest is None and not self.ohlcv_rows:
            raise ValueError("manifest or ohlcv_rows is required")
        return self


class OfflineStrategyPipelineResult(_BaseSafety):
    template_catalog: list[OfflineStrategyTemplate] = Field(default_factory=list)
    dataset_compatibility_report: OfflineStrategyDatasetCompatibilityReport
    training_plan: OfflineStrategyTrainingLaunchPlan
    candidates: list[OfflineStrategyCandidate] = Field(default_factory=list)
    walk_forward_result: OfflineStrategyWalkForwardResult
    signals: list[OfflineStrategySignal] = Field(default_factory=list)
    intents: list[OfflineStrategyTradeIntent] = Field(default_factory=list)
    backtest_results: list[OfflineStrategyBacktestResult] = Field(default_factory=list)
    metric_summaries: list[OfflineStrategyMetricSummary] = Field(default_factory=list)
    promotion_decisions: list[OfflineStrategyPromotionDecision] = Field(default_factory=list)
    artifact_manifest: OfflineStrategyArtifactManifest
    safety_report: OfflineStrategySafetyReport
    gap_report: OfflineStrategyGapReport

    @model_validator(mode="after")
    def validate_result(self):
        return _validate_safety_flags(self, "pipeline result")
