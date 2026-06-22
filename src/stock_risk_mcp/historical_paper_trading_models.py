from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_paper_trading_guard import validate_historical_paper_trading_metadata_safety
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def _upper_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip().upper()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _string_required(value, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_positive_number(value, field_name: str, *, zero_allowed: bool = False):
    if zero_allowed:
        if value < 0:
            raise ValueError(f"{field_name} must be greater than or equal to zero")
    else:
        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero")
    return value


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "paper_only",
        "simulated_only",
        "non_executable",
        "local_file_only",
        "offline_only",
        "read_only_input",
        "no_network",
        "no_provider_api",
        "no_real_order",
        "no_real_order_intent",
        "no_broker_api",
        "no_account_api",
        "no_order_api",
        "no_kiwoom_api",
        "no_ls_api",
        "no_live_trading",
        "no_live_prod",
        "no_cloud_llm",
        "no_local_llm_runtime",
        "no_external_execution",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class HistoricalPaperSide(StrEnum):
    PAPER_BUY = "PAPER_BUY"
    PAPER_SELL = "PAPER_SELL"
    PAPER_HOLD = "PAPER_HOLD"
    PAPER_SKIP = "PAPER_SKIP"
    PAPER_CLOSE = "PAPER_CLOSE"


class HistoricalPaperTradingGapCategory(StrEnum):
    PAPER_TRADING_PLAN_GENERATED = "PAPER_TRADING_PLAN_GENERATED"
    PAPER_TRADING_LOCAL_ONLY = "PAPER_TRADING_LOCAL_ONLY"
    PAPER_TRADING_OFFLINE_ONLY = "PAPER_TRADING_OFFLINE_ONLY"
    PAPER_TRADING_PAPER_ONLY = "PAPER_TRADING_PAPER_ONLY"
    PAPER_TRADING_SIMULATED_ONLY = "PAPER_TRADING_SIMULATED_ONLY"
    PAPER_TRADING_NON_EXECUTABLE = "PAPER_TRADING_NON_EXECUTABLE"
    PAPER_TRADING_MISSING_INPUT = "PAPER_TRADING_MISSING_INPUT"
    PAPER_TRADING_MISSING_SIGNAL_CANDIDATE_REF = "PAPER_TRADING_MISSING_SIGNAL_CANDIDATE_REF"
    PAPER_TRADING_MISSING_PRICE_BAR = "PAPER_TRADING_MISSING_PRICE_BAR"
    PAPER_TRADING_MISSING_FILL_PRICE = "PAPER_TRADING_MISSING_FILL_PRICE"
    PAPER_TRADING_MISSING_LEDGER_STATE = "PAPER_TRADING_MISSING_LEDGER_STATE"
    PAPER_TRADING_MISSING_RISK_LIMIT = "PAPER_TRADING_MISSING_RISK_LIMIT"
    PAPER_TRADING_INVALID_INITIAL_CASH = "PAPER_TRADING_INVALID_INITIAL_CASH"
    PAPER_TRADING_INVALID_POSITION_SIZE = "PAPER_TRADING_INVALID_POSITION_SIZE"
    PAPER_TRADING_INVALID_EXPOSURE_LIMIT = "PAPER_TRADING_INVALID_EXPOSURE_LIMIT"
    PAPER_TRADING_INVALID_SLIPPAGE = "PAPER_TRADING_INVALID_SLIPPAGE"
    PAPER_TRADING_INVALID_FEE = "PAPER_TRADING_INVALID_FEE"
    PAPER_TRADING_UNSUPPORTED_PAPER_SIDE = "PAPER_TRADING_UNSUPPORTED_PAPER_SIDE"
    PAPER_TRADING_REAL_ACTION_NOT_ALLOWED = "PAPER_TRADING_REAL_ACTION_NOT_ALLOWED"
    PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED = "PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED"
    PAPER_TRADING_BROKER_PATH_NOT_ALLOWED = "PAPER_TRADING_BROKER_PATH_NOT_ALLOWED"
    PAPER_TRADING_KIWOOM_API_NOT_ALLOWED = "PAPER_TRADING_KIWOOM_API_NOT_ALLOWED"
    PAPER_TRADING_LS_API_NOT_ALLOWED = "PAPER_TRADING_LS_API_NOT_ALLOWED"
    PAPER_TRADING_ACCOUNT_API_NOT_ALLOWED = "PAPER_TRADING_ACCOUNT_API_NOT_ALLOWED"
    PAPER_TRADING_ORDER_API_NOT_ALLOWED = "PAPER_TRADING_ORDER_API_NOT_ALLOWED"
    PAPER_TRADING_NETWORK_NOT_ALLOWED = "PAPER_TRADING_NETWORK_NOT_ALLOWED"
    PAPER_TRADING_PROVIDER_API_NOT_ALLOWED = "PAPER_TRADING_PROVIDER_API_NOT_ALLOWED"
    PAPER_TRADING_LIVE_TRADING_NOT_ALLOWED = "PAPER_TRADING_LIVE_TRADING_NOT_ALLOWED"
    PAPER_TRADING_LIVE_PROD_NOT_ALLOWED = "PAPER_TRADING_LIVE_PROD_NOT_ALLOWED"
    PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED = "PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED"
    PAPER_TRADING_LOCAL_LLM_RUNTIME_NOT_ALLOWED = "PAPER_TRADING_LOCAL_LLM_RUNTIME_NOT_ALLOWED"
    PAPER_TRADING_CREDENTIALS_NOT_ALLOWED = "PAPER_TRADING_CREDENTIALS_NOT_ALLOWED"
    PAPER_TRADING_PARQUET_NOT_ALLOWED = "PAPER_TRADING_PARQUET_NOT_ALLOWED"


class HistoricalPaperTradingConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    initial_cash: float
    slippage_bps: float = Field(default=0.0)
    fee_bps: float = Field(default=0.0)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_config_id(cls, value):
        return _upper_required(value, "config_id")

    @field_validator("initial_cash", mode="after")
    @classmethod
    def validate_initial_cash(cls, value):
        return _validate_positive_number(value, "initial_cash")

    @model_validator(mode="after")
    def validate_config(self):
        if self.strategy_track != StrategyTrack.DOMESTIC_KR:
            raise ValueError("historical paper trading config requires StrategyTrack DOMESTIC_KR")
        return _validate_safety_flags(self, "historical paper trading config")


class HistoricalPaperPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    max_positions: int = Field(..., ge=1)
    max_exposure: float
    max_per_symbol_exposure: float
    max_daily_loss: float
    max_drawdown: float
    default_holding_period_sessions: int = Field(..., ge=1)
    stop_simulation_rule: str = Field(..., min_length=1)
    take_profit_simulation_rule: str = Field(..., min_length=1)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("policy_id", "stop_simulation_rule", "take_profit_simulation_rule", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("max_exposure", "max_per_symbol_exposure", mode="after")
    @classmethod
    def validate_exposure_limits(cls, value, info):
        return _validate_positive_number(value, info.field_name)

    @field_validator("max_daily_loss", "max_drawdown", mode="after")
    @classmethod
    def validate_loss_limits(cls, value, info):
        return _validate_positive_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_policy(self):
        return _validate_safety_flags(self, "historical paper policy")


class HistoricalPaperDecision(StrictModel):
    decision_id: str = Field(..., min_length=1)
    signal_candidate_ref_id: str = Field(..., min_length=1)
    paper_side: HistoricalPaperSide
    decision_timestamp: datetime
    decision_reason: str = Field(..., min_length=1)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("decision_id", "signal_candidate_ref_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("paper_side", mode="before")
    @classmethod
    def validate_paper_side(cls, value):
        try:
            return HistoricalPaperSide(str(value).strip().upper())
        except Exception as exc:
            raise ValueError("paper side must remain paper-only") from exc

    @field_validator("decision_timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @field_validator("decision_reason", mode="before")
    @classmethod
    def validate_reason(cls, value):
        return _string_required(value, "decision_reason")

    @model_validator(mode="after")
    def validate_decision(self):
        return _validate_safety_flags(self, "historical paper decision")


class HistoricalPaperOrderIntent(StrictModel):
    paper_order_intent_id: str = Field(..., min_length=1)
    signal_candidate_ref_id: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    paper_side: HistoricalPaperSide
    symbol: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    decision_timestamp: datetime
    intended_entry_session: date
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_order_intent_id", "signal_candidate_ref_id", "decision_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("paper_side", mode="before")
    @classmethod
    def validate_paper_side(cls, value):
        try:
            return HistoricalPaperSide(str(value).strip().upper())
        except Exception as exc:
            raise ValueError("paper side must remain paper-only") from exc

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "symbol")

    @field_validator("decision_timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @model_validator(mode="after")
    def validate_order_intent(self):
        return _validate_safety_flags(self, "historical paper order intent")


class HistoricalPaperFill(StrictModel):
    paper_fill_id: str = Field(..., min_length=1)
    paper_order_intent_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    paper_side: HistoricalPaperSide
    fill_price: float
    fill_quantity: int = Field(..., ge=1)
    fill_timestamp: datetime
    slippage_cost: float = Field(default=0.0)
    fee_cost: float = Field(default=0.0)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_fill_id", "paper_order_intent_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("paper_side", mode="before")
    @classmethod
    def validate_paper_side(cls, value):
        try:
            return HistoricalPaperSide(str(value).strip().upper())
        except Exception as exc:
            raise ValueError("paper side must remain paper-only") from exc

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "symbol")

    @field_validator("fill_price", "slippage_cost", "fee_cost", mode="after")
    @classmethod
    def validate_non_negative(cls, value, info):
        return _validate_positive_number(value, info.field_name, zero_allowed=True)

    @field_validator("fill_timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        return aware(value)

    @model_validator(mode="after")
    def validate_fill(self):
        return _validate_safety_flags(self, "historical paper fill")


class HistoricalPaperLedger(StrictModel):
    paper_ledger_id: str = Field(..., min_length=1)
    starting_cash: float
    cash_balance: float
    reserved_cash: float
    realized_pnl: float
    unrealized_pnl: float
    fees_paid: float
    slippage_paid: float
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_ledger_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "paper_ledger_id")

    @field_validator("starting_cash", "cash_balance", "reserved_cash", "fees_paid", "slippage_paid", mode="after")
    @classmethod
    def validate_cash_fields(cls, value, info):
        return _validate_positive_number(value, info.field_name, zero_allowed=True)

    @model_validator(mode="after")
    def validate_ledger(self):
        return _validate_safety_flags(self, "historical paper ledger")


class HistoricalPaperPosition(StrictModel):
    paper_position_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    open_quantity: int = Field(..., ge=0)
    average_entry_price: float
    market_value: float
    unrealized_pnl: float
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_position_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "paper_position_id")

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "symbol")

    @field_validator("average_entry_price", "market_value", mode="after")
    @classmethod
    def validate_values(cls, value, info):
        return _validate_positive_number(value, info.field_name, zero_allowed=True)

    @model_validator(mode="after")
    def validate_position(self):
        return _validate_safety_flags(self, "historical paper position")


class HistoricalPaperTrade(StrictModel):
    paper_trade_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    entry_fill_id: str = Field(..., min_length=1)
    entry_side: HistoricalPaperSide
    entry_price: float
    entry_quantity: int = Field(..., ge=1)
    status: str = Field(..., min_length=1)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_trade_id", "entry_fill_id", "status", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return _string_required(value, "symbol")

    @field_validator("entry_side", mode="before")
    @classmethod
    def validate_entry_side(cls, value):
        try:
            return HistoricalPaperSide(str(value).strip().upper())
        except Exception as exc:
            raise ValueError("paper side must remain paper-only") from exc

    @field_validator("entry_price", mode="after")
    @classmethod
    def validate_entry_price(cls, value):
        return _validate_positive_number(value, "entry_price", zero_allowed=True)

    @model_validator(mode="after")
    def validate_trade(self):
        return _validate_safety_flags(self, "historical paper trade")


class HistoricalPaperRiskLimit(StrictModel):
    paper_risk_limit_id: str = Field(..., min_length=1)
    max_positions: int = Field(..., ge=1)
    max_exposure: float
    max_per_symbol_exposure: float
    max_daily_loss: float
    max_drawdown: float
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("paper_risk_limit_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "paper_risk_limit_id")

    @field_validator("max_exposure", "max_per_symbol_exposure", "max_daily_loss", "max_drawdown", mode="after")
    @classmethod
    def validate_limits(cls, value, info):
        return _validate_positive_number(value, info.field_name)

    @model_validator(mode="after")
    def validate_risk_limit(self):
        return _validate_safety_flags(self, "historical paper risk limit")


class HistoricalPaperPerformanceReport(StrictModel):
    performance_report_id: str = Field(..., min_length=1)
    total_return: float
    realized_pnl: float
    unrealized_pnl: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    turnover: float
    exposure_time: float
    fees: float
    slippage_cost: float
    number_of_trades: int = Field(..., ge=0)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("performance_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "performance_report_id")

    @field_validator("max_drawdown", "win_rate", "profit_factor", "average_win", "average_loss", "turnover", "exposure_time", "fees", "slippage_cost", mode="after")
    @classmethod
    def validate_non_negative(cls, value, info):
        return _validate_positive_number(value, info.field_name, zero_allowed=True)

    @model_validator(mode="after")
    def validate_performance(self):
        return _validate_safety_flags(self, "historical paper performance report")


class HistoricalPaperTradingSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    paper_trading_input_id: str = Field(..., min_length=1)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("safety_report_id", "paper_trading_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_safety_report(self):
        return _validate_safety_flags(self, "historical paper trading safety report")


class HistoricalPaperTradingGapReport(StrictModel):
    gap_report_id: str = Field(..., min_length=1)
    paper_trading_input_id: str = Field(..., min_length=1)
    gap_status: str = Field(default="NO_GAPS", min_length=1)
    gap_categories: list[str] = Field(default_factory=list)
    blocking_gap_count: int = Field(default=0, ge=0)
    report_only_gap_count: int = Field(default=0, ge=0)
    gaps: list[dict[str, str]] = Field(default_factory=list)
    paper_only: bool = True
    simulated_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    offline_only: bool = True
    read_only_input: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_real_order: bool = True
    no_real_order_intent: bool = True
    no_broker_api: bool = True
    no_account_api: bool = True
    no_order_api: bool = True
    no_kiwoom_api: bool = True
    no_ls_api: bool = True
    no_live_trading: bool = True
    no_live_prod: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True
    no_external_execution: bool = True

    @field_validator("gap_report_id", "paper_trading_input_id", "gap_status", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_gap_report(self):
        return _validate_safety_flags(self, "historical paper trading gap report")


class HistoricalPaperTradingAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    paper_trading_input_id: str = Field(..., min_length=1)
    created_at: datetime
    operator_context: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)

    @field_validator("audit_record_id", "paper_trading_input_id", "operator_context", mode="before")
    @classmethod
    def normalize_fields(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value):
        return aware(value)

    @field_validator("source_path", mode="before")
    @classmethod
    def validate_source_path(cls, value):
        return _validate_local_path(value, "source_path")


class HistoricalPaperTradingInput(StrictModel):
    schema_version: str = Field(..., min_length=1)
    paper_trading_input_id: str = Field(..., min_length=1)
    paper_trading_config: HistoricalPaperTradingConfig
    paper_policy: HistoricalPaperPolicy
    paper_decision: HistoricalPaperDecision
    paper_order_intent: HistoricalPaperOrderIntent
    paper_fill: HistoricalPaperFill
    paper_ledger: HistoricalPaperLedger
    paper_position: HistoricalPaperPosition
    paper_trade: HistoricalPaperTrade
    paper_risk_limit: HistoricalPaperRiskLimit
    paper_performance_report: HistoricalPaperPerformanceReport
    safety_report: HistoricalPaperTradingSafetyReport
    gap_report: HistoricalPaperTradingGapReport
    audit_records: list[HistoricalPaperTradingAuditRecord] = Field(default_factory=list)
    paper_runtime_context: dict[str, object] = Field(default_factory=dict)

    @field_validator("schema_version", "paper_trading_input_id", mode="before")
    @classmethod
    def normalize_ids(cls, value, info):
        return _upper_required(value, info.field_name)
