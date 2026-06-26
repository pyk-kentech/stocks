from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

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
        raise ValueError(f"{field_name} must be relative or sanitized")
    if ".." in path.parts:
        raise ValueError(f"{field_name} must not contain path traversal")
    return cleaned


def _validate_scalar_map(
    value: dict[str, Any],
    field_name: str,
    *,
    allow_label_like_names: bool = False,
) -> dict[str, ScalarValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    blocked_name_markers = (
        "credential",
        "token",
        "secret",
        "account",
        "order",
    )
    label_like_markers = (
        "forward_return",
        "future_return",
        "mfe",
        "mae",
        "target",
        "label",
        "outcome",
    )
    normalized: dict[str, ScalarValue] = {}
    for key, raw in value.items():
        name = _string_required(key, f"{field_name}.key")
        lowered = name.lower()
        if any(marker in lowered for marker in blocked_name_markers):
            raise ValueError(f"{field_name} contains blocked field name: {name}")
        if not allow_label_like_names and any(marker in lowered for marker in label_like_markers):
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
        "no_paper_trading",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class FeatureStoreBackend(StrEnum):
    IN_MEMORY = "IN_MEMORY"
    JSON = "JSON"
    PARQUET = "PARQUET"
    DUCKDB = "DUCKDB"
    POLARS = "POLARS"


class FeatureStoreBackendStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    DISABLED_BY_POLICY = "DISABLED_BY_POLICY"
    SCHEMA_GAP = "SCHEMA_GAP"
    DEPENDENCY_GAP = "DEPENDENCY_GAP"
    BACKEND_GAP = "BACKEND_GAP"
    REJECTED = "REJECTED"


class FeatureStoreFormat(StrEnum):
    JSON = "JSON"
    JSONL = "JSONL"
    PARQUET = "PARQUET"
    DUCKDB_TABLE = "DUCKDB_TABLE"
    POLARS_FRAME = "POLARS_FRAME"


class FeatureStoreRootPolicy(StrEnum):
    SAFE_LOCAL_ROOT_ONLY = "SAFE_LOCAL_ROOT_ONLY"
    TEST_TEMP_ONLY = "TEST_TEMP_ONLY"
    REJECTED_PATH = "REJECTED_PATH"


class FeatureStoreDatasetProfile(StrEnum):
    SMOKE_PROFILE = "SMOKE_PROFILE"
    DAILY_RESEARCH_PROFILE = "DAILY_RESEARCH_PROFILE"
    INTRADAY_CANDIDATE_PROFILE = "INTRADAY_CANDIDATE_PROFILE"
    FULL_INTRADAY_PROFILE = "FULL_INTRADAY_PROFILE"


class FeatureStoreSourceKind(StrEnum):
    V7_POINT_IN_TIME_UNIVERSE_CONTEXT = "V7_POINT_IN_TIME_UNIVERSE_CONTEXT"
    V7_WALK_FORWARD_GUARD_CONTEXT = "V7_WALK_FORWARD_GUARD_CONTEXT"
    V7_TRAINING_PROMOTION_CONTEXT = "V7_TRAINING_PROMOTION_CONTEXT"
    V8_DOMESTIC_STOCK_SNAPSHOT = "V8_DOMESTIC_STOCK_SNAPSHOT"
    V8_CAPTURED_KIWOOM_CHART_HISTORY = "V8_CAPTURED_KIWOOM_CHART_HISTORY"
    V8_MANUAL_IMPORTED_KIWOOM_CHART_HISTORY = "V8_MANUAL_IMPORTED_KIWOOM_CHART_HISTORY"
    V9_MACRO_REGIME_SNAPSHOT = "V9_MACRO_REGIME_SNAPSHOT"
    V9_REGIME_CLASSIFICATION = "V9_REGIME_CLASSIFICATION"
    V9_MACRO_EVENT_WINDOW = "V9_MACRO_EVENT_WINDOW"
    V7_POSITION_SIZING_CONTEXT = "V7_POSITION_SIZING_CONTEXT"
    V7_EVENT_RISK_CONTEXT = "V7_EVENT_RISK_CONTEXT"
    V7_OUTLIER_ROUTING_CONTEXT = "V7_OUTLIER_ROUTING_CONTEXT"
    MANUAL_LABEL_FIXTURE = "MANUAL_LABEL_FIXTURE"
    MANUAL_PRICE_HISTORY_FIXTURE = "MANUAL_PRICE_HISTORY_FIXTURE"
    LOCAL_PRICE_HISTORY_FIXTURE = "LOCAL_PRICE_HISTORY_FIXTURE"
    UNKNOWN = "UNKNOWN"


class FeatureStoreFeatureNamespace(StrEnum):
    DOMESTIC_PRICE = "domestic.price"
    DOMESTIC_OHLCV = "domestic.ohlcv"
    DOMESTIC_LIQUIDITY = "domestic.liquidity"
    DOMESTIC_ORDERBOOK = "domestic.orderbook"
    DOMESTIC_RANK = "domestic.rank"
    DOMESTIC_OUTLIER = "domestic.outlier"
    DOMESTIC_FLOW = "domestic.flow"
    DOMESTIC_PROGRAM = "domestic.program"
    DOMESTIC_SHORT_LENDING_CAPABILITY = "domestic.short_lending_capability"
    DOMESTIC_THEME = "domestic.theme"
    DOMESTIC_ETF = "domestic.etf"
    DOMESTIC_SNAPSHOT_QUALITY = "domestic.snapshot_quality"
    MACRO_NQ = "macro.nq"
    MACRO_ES = "macro.es"
    MACRO_VIX = "macro.vix"
    MACRO_DOLLAR_STRENGTH = "macro.dollar_strength"
    MACRO_US10Y = "macro.us10y"
    MACRO_USDKRW = "macro.usdkrw"
    MACRO_EVENT_WINDOW = "macro.event_window"
    MACRO_REGIME_CLASSIFICATION = "macro.regime_classification"
    MACRO_PROVIDER_GAP = "macro.provider_gap"
    MACRO_FRESHNESS = "macro.freshness"
    RISK_POSITION_SIZING_CONTEXT = "risk.position_sizing_context"
    RISK_EVENT_RISK_CONTEXT = "risk.event_risk_context"
    RISK_OUTLIER_ROUTING_CONTEXT = "risk.outlier_routing_context"
    RISK_TRAINING_GUARD_CONTEXT = "risk.training_guard_context"
    META_INSTRUMENT = "meta.instrument"
    META_MARKET = "meta.market"
    META_CURRENCY = "meta.currency"
    META_OBSERVED_AT = "meta.observed_at"
    META_AVAILABLE_AT = "meta.available_at"
    META_SNAPSHOT_AT = "meta.snapshot_at"
    META_SOURCE_REF = "meta.source_ref"
    META_LINEAGE = "meta.lineage"
    META_NON_EXECUTABLE = "meta.non_executable"


class FeatureStoreReadinessStatus(StrEnum):
    FEATURE_ROWS_READY = "FEATURE_ROWS_READY"
    MANUAL_LABELS_READY = "MANUAL_LABELS_READY"
    DETERMINISTIC_LABELS_READY = "DETERMINISTIC_LABELS_READY"
    DATA_GAP = "DATA_GAP"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    LABEL_GAP = "LABEL_GAP"
    UNLABELED_DATASET_READY = "UNLABELED_DATASET_READY"
    LABELED_DATASET_READY = "LABELED_DATASET_READY"
    TRAINING_DATASET_MANIFEST_READY = "TRAINING_DATASET_MANIFEST_READY"
    MATERIALIZATION_READY = "MATERIALIZATION_READY"
    DEPENDENCY_GAP = "DEPENDENCY_GAP"
    BACKEND_GAP = "BACKEND_GAP"
    BLOCKED_LEAKAGE = "BLOCKED_LEAKAGE"
    BLOCKED_SURVIVORSHIP = "BLOCKED_SURVIVORSHIP"
    BLOCKED_DATA_SNOOPING = "BLOCKED_DATA_SNOOPING"
    RESEARCH_ONLY = "RESEARCH_ONLY"


class FeatureStoreLabelDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    DIRECTIONLESS = "DIRECTIONLESS"
    UNKNOWN = "UNKNOWN"


class FeatureStoreLabelDerivationMethod(StrEnum):
    MANUAL_FIXTURE = "MANUAL_FIXTURE"
    LOCAL_PRICE_HISTORY_FORWARD_RETURN = "LOCAL_PRICE_HISTORY_FORWARD_RETURN"
    LOCAL_PRICE_HISTORY_FORWARD_LOG_RETURN = "LOCAL_PRICE_HISTORY_FORWARD_LOG_RETURN"
    LOCAL_PRICE_HISTORY_MFE = "LOCAL_PRICE_HISTORY_MFE"
    LOCAL_PRICE_HISTORY_MAE = "LOCAL_PRICE_HISTORY_MAE"
    LOCAL_PRICE_HISTORY_VOL_ADJUSTED_RETURN = "LOCAL_PRICE_HISTORY_VOL_ADJUSTED_RETURN"
    LOCAL_PRICE_HISTORY_OUTLIER_CONTINUATION = "LOCAL_PRICE_HISTORY_OUTLIER_CONTINUATION"


class FeatureStoreAnchorPricePolicy(StrEnum):
    LAST_AVAILABLE_CLOSE = "LAST_AVAILABLE_CLOSE"
    LAST_AVAILABLE_BAR_CLOSE = "LAST_AVAILABLE_BAR_CLOSE"
    NEXT_OPEN_AFTER_ASOF = "NEXT_OPEN_AFTER_ASOF"
    EXPLICIT_MANUAL_ANCHOR = "EXPLICIT_MANUAL_ANCHOR"
    UNKNOWN_ANCHOR_POLICY = "UNKNOWN_ANCHOR_POLICY"


class FeatureStoreLabelHorizonPolicy(StrEnum):
    TRADING_SESSION = "TRADING_SESSION"
    CALENDAR_DAY = "CALENDAR_DAY"
    BAR_COUNT = "BAR_COUNT"
    EXPLICIT_FIXTURE_POLICY = "EXPLICIT_FIXTURE_POLICY"
    UNKNOWN_HORIZON_POLICY = "UNKNOWN_HORIZON_POLICY"


class FeatureStoreSplitRole(StrEnum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"
    HOLDOUT = "HOLDOUT"
    EXCLUDED = "EXCLUDED"


class FeatureStoreSplitMode(StrEnum):
    ANCHORED = "ANCHORED"
    ROLLING = "ROLLING"


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
    no_paper_trading: bool = True


class FeatureStorePartitionSpec(StrictModel):
    partition_keys: list[str] = Field(default_factory=list)

    @field_validator("partition_keys", mode="before")
    @classmethod
    def normalize_keys(cls, value):
        return _normalize_list(value, "partition_keys", upper=True)


class FeatureStoreSourceRef(StrictModel):
    source_id: str = Field(..., min_length=1)
    source_kind: FeatureStoreSourceKind
    sanitized_basename: str = Field(..., min_length=1)
    relative_path: str | None = None
    available_at: datetime | None = None

    @field_validator("source_id", "sanitized_basename", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("relative_path", mode="before")
    @classmethod
    def normalize_relative_path(cls, value):
        return _validate_relative_path(value, "relative_path")

    @field_validator("available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class FeatureStoreLineageRecord(StrictModel):
    lineage_id: str = Field(..., min_length=1)
    source_ref: FeatureStoreSourceRef
    stage: str = Field(..., min_length=1)
    source_available_at: datetime | None = None
    feature_names: list[str] = Field(default_factory=list)

    @field_validator("lineage_id", "stage", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("source_available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("feature_names", mode="before")
    @classmethod
    def normalize_names(cls, value):
        return _normalize_list(value, "feature_names")


class FeatureStoreFeatureColumn(StrictModel):
    column_name: str = Field(..., min_length=1)
    namespace: FeatureStoreFeatureNamespace
    dtype: str = Field(..., min_length=1)
    nullable: bool = True
    leakage_sensitive: bool = False
    description: str | None = None

    @field_validator("column_name", "dtype", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value):
        if value is None:
            return None
        return _string_required(value, "description")


class FeatureStoreFeatureSchema(StrictModel):
    schema_id: str = Field(..., min_length=1)
    dataset_profile: FeatureStoreDatasetProfile
    columns: list[FeatureStoreFeatureColumn] = Field(default_factory=list)

    @field_validator("schema_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "schema_id")


class FeatureStoreFeatureRow(_BaseSafety):
    dataset_id: str = Field(..., min_length=1)
    row_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    feature_asof: datetime
    available_at: datetime
    snapshot_at: datetime | None = None
    feature_namespace: FeatureStoreFeatureNamespace
    feature_values: dict[str, ScalarValue] = Field(default_factory=dict)
    feature_availability_map: dict[str, str] = Field(default_factory=dict)
    source_refs: list[FeatureStoreSourceRef] = Field(default_factory=list)
    lineage_records: list[FeatureStoreLineageRecord] = Field(default_factory=list)
    source_kind: FeatureStoreSourceKind

    @field_validator("dataset_id", "row_id", "instrument_id", "market", "currency", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("feature_asof", "available_at", "snapshot_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("feature_values", mode="before")
    @classmethod
    def normalize_feature_values(cls, value):
        return _validate_scalar_map(value or {}, "feature_values", allow_label_like_names=True)

    @field_validator("feature_availability_map", mode="before")
    @classmethod
    def normalize_availability_map(cls, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("feature_availability_map must be a dict")
        return {str(k): _aware(v).isoformat() for k, v in value.items()}

    @model_validator(mode="after")
    def validate_row(self):
        if self.available_at > self.feature_asof:
            raise ValueError("feature row available_at must be <= feature_asof")
        return _validate_safety_flags(self, "feature row")


class FeatureStoreLabelSpec(StrictModel):
    label_name: str = Field(..., min_length=1)
    label_horizon: str = Field(..., min_length=1)
    label_horizon_policy: FeatureStoreLabelHorizonPolicy = FeatureStoreLabelHorizonPolicy.TRADING_SESSION
    derivation_method: FeatureStoreLabelDerivationMethod
    label_direction: FeatureStoreLabelDirection = FeatureStoreLabelDirection.LONG
    anchor_price_policy: FeatureStoreAnchorPricePolicy = FeatureStoreAnchorPricePolicy.LAST_AVAILABLE_CLOSE

    @field_validator("label_name", "label_horizon", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)


class FeatureStorePriceBar(StrictModel):
    instrument_id: str = Field(..., min_length=1)
    observed_at: datetime
    available_at: datetime
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    close_price: float = Field(..., gt=0)
    volume: float | None = Field(default=None, ge=0)
    source_ref: FeatureStoreSourceRef

    @field_validator("instrument_id", mode="before")
    @classmethod
    def normalize_instrument(cls, value):
        return _upper_required(value, "instrument_id")

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class FeatureStoreLabelRow(_BaseSafety):
    dataset_id: str = Field(..., min_length=1)
    label_row_id: str = Field(..., min_length=1)
    row_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    label_name: str = Field(..., min_length=1)
    label_horizon: str = Field(..., min_length=1)
    label_horizon_policy: FeatureStoreLabelHorizonPolicy
    label_value: float | str | bool | None = None
    label_unit: str = Field(..., min_length=1)
    label_direction: FeatureStoreLabelDirection = FeatureStoreLabelDirection.UNKNOWN
    label_window_start: datetime
    label_window_end: datetime
    label_observed_at: datetime
    label_available_at: datetime
    label_input_source_kind: FeatureStoreSourceKind
    label_input_source_ref: FeatureStoreSourceRef
    derivation_method: FeatureStoreLabelDerivationMethod
    anchor_price: float | None = None
    anchor_observed_at: datetime | None = None
    anchor_available_at: datetime | None = None
    anchor_source_ref: FeatureStoreSourceRef | None = None
    anchor_price_policy: FeatureStoreAnchorPricePolicy = FeatureStoreAnchorPricePolicy.UNKNOWN_ANCHOR_POLICY
    quality_flags: list[str] = Field(default_factory=list)

    @field_validator("dataset_id", "label_row_id", "row_id", "instrument_id", "label_name", "label_horizon", "label_unit", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator(
        "label_window_start",
        "label_window_end",
        "label_observed_at",
        "label_available_at",
        "anchor_observed_at",
        "anchor_available_at",
        mode="before",
    )
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value):
        return _normalize_list(value, "quality_flags", upper=True)

    @model_validator(mode="after")
    def validate_row(self):
        if self.label_available_at <= self.label_observed_at:
            raise ValueError("label_available_at must be after label_observed_at")
        if self.label_window_end < self.label_window_start:
            raise ValueError("label window end must be after start")
        return _validate_safety_flags(self, "label row")


class FeatureStoreTrainingRow(_BaseSafety):
    dataset_id: str = Field(..., min_length=1)
    training_row_id: str = Field(..., min_length=1)
    row_id: str = Field(..., min_length=1)
    instrument_id: str = Field(..., min_length=1)
    split_id: str = Field(..., min_length=1)
    split_role: FeatureStoreSplitRole
    label_row_ids: list[str] = Field(default_factory=list)
    label_values: dict[str, ScalarValue] = Field(default_factory=dict)
    labeled: bool = False
    blocked_from_training: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    label_gap_reasons: list[str] = Field(default_factory=list)

    @field_validator("dataset_id", "training_row_id", "row_id", "instrument_id", "split_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("label_row_ids", "blocking_reasons", "label_gap_reasons", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @field_validator("label_values", mode="before")
    @classmethod
    def normalize_label_values(cls, value):
        return _validate_scalar_map(value or {}, "label_values", allow_label_like_names=True)

    @model_validator(mode="after")
    def validate_row(self):
        if self.labeled and not self.label_row_ids:
            raise ValueError("labeled training row requires label_row_ids")
        return _validate_safety_flags(self, "training row")


class FeatureStoreSourceFeatureInput(StrictModel):
    source_row_id: str = Field(..., min_length=1)
    source_kind: FeatureStoreSourceKind
    instrument_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    feature_asof: datetime
    available_at: datetime
    snapshot_at: datetime | None = None
    feature_namespace: FeatureStoreFeatureNamespace
    feature_values: dict[str, ScalarValue] = Field(default_factory=dict)
    source_ref: FeatureStoreSourceRef

    @field_validator("source_row_id", "instrument_id", "market", "currency", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("feature_asof", "available_at", "snapshot_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("feature_values", mode="before")
    @classmethod
    def normalize_values(cls, value):
        return _validate_scalar_map(value or {}, "feature_values", allow_label_like_names=True)


class FeatureStoreWalkForwardSplit(StrictModel):
    split_id: str = Field(..., min_length=1)
    split_mode: FeatureStoreSplitMode
    split_role: FeatureStoreSplitRole
    start_at: datetime | None = None
    end_at: datetime | None = None
    row_ids: list[str] = Field(default_factory=list)
    purge_window_count: int = Field(default=0, ge=0)
    embargo_window_count: int = Field(default=0, ge=0)

    @field_validator("split_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "split_id")

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("row_ids", mode="before")
    @classmethod
    def normalize_rows(cls, value):
        return _normalize_list(value, "row_ids", upper=True)


class FeatureStoreWalkForwardPlan(_BaseSafety):
    plan_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    dataset_profile: FeatureStoreDatasetProfile
    split_mode: FeatureStoreSplitMode
    splits: list[FeatureStoreWalkForwardSplit] = Field(default_factory=list)
    max_label_horizon: str = Field(..., min_length=1)

    @field_validator("plan_id", "dataset_id", "max_label_horizon", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_plan(self):
        return _validate_safety_flags(self, "walk forward plan")


class FeatureStoreLeakageReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: FeatureStoreReadinessStatus
    blocked_row_ids: list[str] = Field(default_factory=list)
    warning_row_ids: list[str] = Field(default_factory=list)
    leakage_categories: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("blocked_row_ids", "warning_row_ids", "leakage_categories", "findings", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "leakage report")


class FeatureStoreCompletenessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    required_source_kinds: list[str] = Field(default_factory=list)
    present_source_kinds: list[str] = Field(default_factory=list)
    missing_source_kinds: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("required_source_kinds", "present_source_kinds", "missing_source_kinds", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name, upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "completeness report")


class FeatureStoreFreshnessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    stale_row_ids: list[str] = Field(default_factory=list)
    latest_feature_asof: datetime | None = None

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("stale_row_ids", mode="before")
    @classmethod
    def normalize_rows(cls, value):
        return _normalize_list(value, "stale_row_ids", upper=True)

    @field_validator("latest_feature_asof", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "freshness report")


class FeatureStoreBackendCapabilityRow(StrictModel):
    backend: FeatureStoreBackend
    status: FeatureStoreBackendStatus
    missing_modules: list[str] = Field(default_factory=list)
    allowed_formats: list[FeatureStoreFormat] = Field(default_factory=list)
    root_policy: FeatureStoreRootPolicy
    dataset_profile_compatible: bool = True
    notes: str = Field(..., min_length=1)

    @field_validator("missing_modules", mode="before")
    @classmethod
    def normalize_modules(cls, value):
        return _normalize_list(value, "missing_modules", upper=True)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _string_required(value, "notes")


class FeatureStoreBackendCapabilityReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_profile: FeatureStoreDatasetProfile
    rows: list[FeatureStoreBackendCapabilityRow] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "backend capability report")


class FeatureStoreCacheManifest(_BaseSafety):
    manifest_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    dataset_profile: FeatureStoreDatasetProfile
    cache_root: str = Field(..., min_length=1)
    partition_spec: FeatureStorePartitionSpec
    cached_row_count: int = Field(default=0, ge=0)
    root_policy: FeatureStoreRootPolicy

    @field_validator("manifest_id", "dataset_id", "cache_root", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        if info.field_name == "cache_root":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "cache manifest")


class FeatureStoreDatasetManifest(_BaseSafety):
    dataset_id: str = Field(..., min_length=1)
    schema_version: str = Field(..., min_length=1)
    created_at: datetime
    generator_version: str = Field(..., min_length=1)
    dataset_profile: FeatureStoreDatasetProfile
    feature_schema_ref: str = Field(..., min_length=1)
    row_count: int = Field(default=0, ge=0)
    source_refs: list[FeatureStoreSourceRef] = Field(default_factory=list)
    freshness_summary: str = Field(..., min_length=1)
    completeness_summary: str = Field(..., min_length=1)
    readiness_status: FeatureStoreReadinessStatus

    @field_validator("dataset_id", "schema_version", "generator_version", "feature_schema_ref", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("freshness_summary", "completeness_summary", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "dataset manifest")


class FeatureStoreTrainingDatasetManifest(FeatureStoreDatasetManifest):
    training_row_count: int = Field(default=0, ge=0)
    labeled_row_count: int = Field(default=0, ge=0)
    unlabeled_row_count: int = Field(default=0, ge=0)
    row_count_by_split: dict[str, int] = Field(default_factory=dict)
    label_count_by_horizon: dict[str, int] = Field(default_factory=dict)
    label_coverage_summary: str = Field(..., min_length=1)
    split_coverage_summary: str = Field(..., min_length=1)
    lineage_summary: str = Field(..., min_length=1)
    leakage_summary: str = Field(..., min_length=1)
    survivorship_readiness_summary: str = Field(..., min_length=1)
    backend_capability_summary: str = Field(..., min_length=1)
    materialization_summary: str = Field(..., min_length=1)

    @field_validator(
        "label_coverage_summary",
        "split_coverage_summary",
        "lineage_summary",
        "leakage_summary",
        "survivorship_readiness_summary",
        "backend_capability_summary",
        "materialization_summary",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)


class FeatureStoreV7IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    v71_point_in_time_universe_ready: bool = False
    v72_walk_forward_guard_ready: bool = False
    v73_training_promotion_ready: bool = False
    v710_position_sizing_context_ready: bool = False
    v711_event_risk_feature_ready: bool = False
    v712_outlier_leadership_feature_ready: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v7 integration report")


class FeatureStoreV8IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    domestic_snapshot_feature_ready: bool = False
    local_kiwoom_chart_label_source_ready: bool = False
    v8_lineage_source_coverage_ready: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v8 integration report")


class FeatureStoreV9IntegrationReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    macro_snapshot_feature_ready: bool = False
    regime_classification_feature_ready: bool = False
    macro_event_window_feature_ready: bool = False
    macro_provider_gap_propagated: bool = False

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "v9 integration report")


class FeatureStoreMaterializationPlan(_BaseSafety):
    plan_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    store_root: str = Field(..., min_length=1)
    requested_backends: list[FeatureStoreBackend] = Field(default_factory=list)
    partition_spec: FeatureStorePartitionSpec

    @field_validator("plan_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("store_root", mode="before")
    @classmethod
    def normalize_root(cls, value):
        return _string_required(value, "store_root")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "materialization plan")


class FeatureStoreMaterializationResult(_BaseSafety):
    result_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    requested_backends: list[FeatureStoreBackend] = Field(default_factory=list)
    selected_backend: FeatureStoreBackend
    status: FeatureStoreBackendStatus
    materialized_paths: list[str] = Field(default_factory=list)
    row_count_written: int = Field(default=0, ge=0)
    root_policy: FeatureStoreRootPolicy
    degradation_reasons: list[str] = Field(default_factory=list)

    @field_validator("result_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("materialized_paths", "degradation_reasons", mode="before")
    @classmethod
    def normalize_lists(cls, value, info):
        return _normalize_list(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "materialization result")


class FeatureStoreTrainingReadinessReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: FeatureStoreReadinessStatus
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
    def validate_report(self):
        return _validate_safety_flags(self, "training readiness report")


class FeatureStoreSafetyReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @field_validator("findings", mode="before")
    @classmethod
    def normalize_findings(cls, value):
        return _normalize_list(value, "findings", upper=True)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "safety report")


class FeatureStoreGapEntry(StrictModel):
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


class FeatureStoreGapReport(_BaseSafety):
    report_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    readiness_status: FeatureStoreReadinessStatus
    gap_entries: list[FeatureStoreGapEntry] = Field(default_factory=list)

    @field_validator("report_id", "dataset_id", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "gap report")


class FeatureStoreAuditRecord(StrictModel):
    audit_record_id: str = Field(..., min_length=1)
    created_at: datetime
    source_path: str = Field(..., min_length=1)
    operator_context: str = Field(..., min_length=1)
    redaction_applied: bool = True
    contains_secret_material: bool = False
    contains_token_material: bool = False
    contains_account_material: bool = False

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("created_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_path", "operator_context", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)


class FeatureStorePipelineInput(_BaseSafety):
    pipeline_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    schema_version: str = Field(default="V10.0", min_length=1)
    generator_version: str = Field(default="V10.0", min_length=1)
    dataset_profile: FeatureStoreDatasetProfile = FeatureStoreDatasetProfile.DAILY_RESEARCH_PROFILE
    store_root: str = Field(default="local_data/feature_store", min_length=1)
    capacity_acknowledged: bool = False
    split_mode: FeatureStoreSplitMode = FeatureStoreSplitMode.ANCHORED
    requested_backends: list[FeatureStoreBackend] = Field(default_factory=lambda: [FeatureStoreBackend.IN_MEMORY])
    source_feature_inputs: list[FeatureStoreSourceFeatureInput] = Field(default_factory=list)
    manual_label_rows: list[FeatureStoreLabelRow] = Field(default_factory=list)
    price_history_rows: list[FeatureStorePriceBar] = Field(default_factory=list)
    label_specs: list[FeatureStoreLabelSpec] = Field(default_factory=list)
    partition_spec: FeatureStorePartitionSpec = Field(default_factory=FeatureStorePartitionSpec)
    audit_records: list[FeatureStoreAuditRecord] = Field(default_factory=list)

    @field_validator("pipeline_id", "dataset_id", "schema_version", "generator_version", mode="before")
    @classmethod
    def normalize_upper(cls, value, info):
        return _upper_required(value, info.field_name)

    @field_validator("store_root", mode="before")
    @classmethod
    def normalize_root(cls, value):
        return _string_required(value, "store_root")

    @model_validator(mode="after")
    def validate_input(self):
        if self.dataset_profile == FeatureStoreDatasetProfile.FULL_INTRADAY_PROFILE and not self.capacity_acknowledged:
            raise ValueError("FULL_INTRADAY_PROFILE requires explicit capacity acknowledgment")
        return _validate_safety_flags(self, "feature store pipeline input")


class FeatureStorePipelineResult(StrictModel):
    feature_schema: FeatureStoreFeatureSchema
    feature_rows: list[FeatureStoreFeatureRow]
    label_rows: list[FeatureStoreLabelRow]
    training_rows: list[FeatureStoreTrainingRow]
    cache_manifest: FeatureStoreCacheManifest
    dataset_manifest: FeatureStoreDatasetManifest
    training_dataset_manifest: FeatureStoreTrainingDatasetManifest
    walk_forward_plan: FeatureStoreWalkForwardPlan
    leakage_report: FeatureStoreLeakageReport
    completeness_report: FeatureStoreCompletenessReport
    freshness_report: FeatureStoreFreshnessReport
    backend_capability_report: FeatureStoreBackendCapabilityReport
    v7_integration_report: FeatureStoreV7IntegrationReport
    v8_integration_report: FeatureStoreV8IntegrationReport
    v9_integration_report: FeatureStoreV9IntegrationReport
    materialization_result: FeatureStoreMaterializationResult
    training_readiness_report: FeatureStoreTrainingReadinessReport
    safety_report: FeatureStoreSafetyReport
    gap_report: FeatureStoreGapReport
