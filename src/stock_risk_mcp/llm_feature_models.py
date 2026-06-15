from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def normalized_strings(values: list[str]) -> list[str]:
    cleaned = [value.strip() for value in values]
    if any(not value for value in cleaned):
        raise ValueError("list values must not be blank")
    return sorted(set(cleaned))


def safe_metadata(value):
    forbidden = ("credential", "token", "secret", "api_key", "apikey", "authorization", "cookie", "endpoint", "url", "account")
    if isinstance(value, dict):
        if any(any(term in str(key).lower() for term in forbidden) for key in value):
            raise ValueError("runtime_metadata contains unsafe key")
        for item in value.values():
            safe_metadata(item)
    elif isinstance(value, list):
        for item in value:
            safe_metadata(item)
    return value


def reject_bool(value):
    if isinstance(value, bool):
        raise ValueError("numeric value must not be boolean")
    return value


SAFETY_METADATA = {
    "advisory_only": True,
    "llm_called": False,
    "strategy_weight_changed": False,
    "strategy_decisions_created": False,
    "orders_created": False,
    "gates_bypassed": False,
    "external_network_calls": False,
}


class LLMBackend(StrEnum):
    LOCAL_FIXTURE = "LOCAL_FIXTURE"
    LOCAL_MODEL = "LOCAL_MODEL"
    DISABLED = "DISABLED"


class LLMSignalDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"


class LLMHorizon(StrEnum):
    ONE_DAY = "1D"
    THREE_DAY = "3D"
    FIVE_DAY = "5D"


class LLMPromptVersion(StrictModel):
    prompt_version_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    prompt_checksum: str = Field(..., min_length=1)
    created_at: datetime
    _created = field_validator("created_at")(aware)


class LLMModelVersion(StrictModel):
    model_version_id: str = Field(..., min_length=1)
    backend: LLMBackend
    model_name: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    runtime_metadata: dict = Field(default_factory=dict)
    _safe = field_validator("runtime_metadata")(safe_metadata)


class LLMFeatureSignal(StrictModel):
    ticker: str = Field(..., min_length=1)
    as_of_time: datetime
    source_ids: list[str]
    event_type: str = Field(..., min_length=1)
    theme_tags: list[str]
    direction: LLMSignalDirection
    catalyst_strength_score: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    risk_language_score: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    uncertainty_score: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    related_tickers: list[str]
    summary: str = Field(..., min_length=1)
    evidence_refs: list[str]
    may_create_order: Literal[False]
    may_bypass_gates: Literal[False]
    _as_of = field_validator("as_of_time")(aware)

    @field_validator("catalyst_strength_score", "risk_language_score", "uncertainty_score", mode="before")
    @classmethod
    def numeric_scores(cls, value):
        return reject_bool(value)

    @field_validator("may_create_order", "may_bypass_gates", mode="before")
    @classmethod
    def exact_false(cls, value):
        if value is not False:
            raise ValueError("safety flag must be exactly false")
        return value

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, value):
        return value.strip().upper()

    @field_validator("source_ids", "theme_tags", "evidence_refs")
    @classmethod
    def normalize_lists(cls, values):
        return normalized_strings(values)

    @field_validator("related_tickers")
    @classmethod
    def normalize_related(cls, values):
        return sorted(set(value.strip().upper() for value in normalized_strings(values)))

    @model_validator(mode="after")
    def no_self_relation(self):
        if self.ticker in self.related_tickers:
            raise ValueError("related_tickers may not contain signal ticker")
        return self


class LLMSignalFixture(StrictModel):
    schema_version: Literal["3.4-signals"]
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    prompt_version: LLMPromptVersion
    model_version: LLMModelVersion
    signals: list[LLMFeatureSignal] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @model_validator(mode="after")
    def validate_signals(self):
        keys = set()
        for signal in self.signals:
            if not self.prompt_version.created_at <= signal.as_of_time <= self.created_at:
                raise ValueError("signal timestamp outside fixture boundary")
            key = (signal.ticker, signal.as_of_time, signal.event_type, self.prompt_version.prompt_version_id, self.model_version.model_version_id)
            if key in keys:
                raise ValueError("duplicate signal key")
            keys.add(key)
        return self


class LLMHorizonOutcome(StrictModel):
    horizon: LLMHorizon
    outcome_time: datetime
    future_price: float = Field(..., gt=0, allow_inf_nan=False)
    return_pct: float = Field(..., allow_inf_nan=False)
    max_drawdown_pct: float = Field(..., ge=0, le=100, allow_inf_nan=False)
    _outcome = field_validator("outcome_time")(aware)

    @field_validator("future_price", "return_pct", "max_drawdown_pct", mode="before")
    @classmethod
    def numeric_values(cls, value):
        return reject_bool(value)


class LLMOutcomeSnapshot(StrictModel):
    ticker: str = Field(..., min_length=1)
    as_of_time: datetime
    reference_price: float = Field(..., gt=0, allow_inf_nan=False)
    horizons: list[LLMHorizonOutcome]
    _as_of = field_validator("as_of_time")(aware)

    @field_validator("reference_price", mode="before")
    @classmethod
    def numeric_reference_price(cls, value):
        return reject_bool(value)

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, value):
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_horizons(self):
        if len({item.horizon for item in self.horizons}) != len(self.horizons):
            raise ValueError("duplicate horizon")
        for item in self.horizons:
            if item.outcome_time <= self.as_of_time:
                raise ValueError("outcome_time must be after as_of_time")
            expected = (item.future_price - self.reference_price) / self.reference_price * 100
            if not math.isclose(item.return_pct, expected, abs_tol=1e-9):
                raise ValueError("return_pct does not match prices")
        return self


class LLMOutcomeFixture(StrictModel):
    schema_version: Literal["3.4-outcomes"]
    created_at: datetime
    snapshots: list[LLMOutcomeSnapshot] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @model_validator(mode="after")
    def validate_snapshots(self):
        keys = set()
        for snapshot in self.snapshots:
            key = (snapshot.ticker, snapshot.as_of_time)
            if key in keys:
                raise ValueError("duplicate outcome snapshot")
            keys.add(key)
            if snapshot.as_of_time > self.created_at or any(item.outcome_time > self.created_at for item in snapshot.horizons):
                raise ValueError("outcome timestamp after fixture creation")
        return self


class LLMFeatureStoreResult(StrictModel):
    schema_version: Literal["3.4-feature-store-result"] = "3.4-feature-store-result"
    fixture_checksum: str
    run_id: str
    prompt_version: LLMPromptVersion
    model_version: LLMModelVersion
    signals: list[LLMFeatureSignal]
    signal_count: int
    metadata_json: dict = Field(default_factory=lambda: dict(SAFETY_METADATA))


class LLMSignalEvaluation(StrictModel):
    ticker: str
    as_of_time: datetime
    event_type: str
    prompt_version_id: str
    model_version_id: str
    horizon: LLMHorizon
    direction: LLMSignalDirection
    status: Literal["EVALUATED", "NEEDS_MORE_DATA"]
    confidence: float
    confidence_bucket: Literal["HIGH", "MEDIUM", "LOW"]
    risk_warning_bucket: Literal["HIGH_RISK_WARNING", "LOW_RISK_WARNING"]
    directional_outcome: Literal["HIT", "MISS", "NOT_APPLICABLE", "NEEDS_MORE_DATA"]
    return_pct: float | None = None
    max_drawdown_pct: float | None = None
    metadata_json: dict = Field(default_factory=lambda: dict(SAFETY_METADATA))


class LLMSpilloverEvaluation(StrictModel):
    source_ticker: str
    related_ticker: str
    horizon: LLMHorizon
    status: Literal["EVALUATED", "NEEDS_MORE_DATA"]
    directional_outcome: Literal["HIT", "MISS", "NOT_APPLICABLE", "NEEDS_MORE_DATA"]
    return_pct: float | None = None
    max_drawdown_pct: float | None = None


class LLMAggregateMetric(StrictModel):
    sample_status: Literal["SUFFICIENT_SAMPLE", "INSUFFICIENT_SAMPLE"]
    available_count: int
    missing_count: int
    missing_data_rate: float
    mean_return_pct: float | None = None
    median_return_pct: float | None = None
    hit_rate: float | None = None
    mean_drawdown_pct: float | None = None
    median_drawdown_pct: float | None = None
    neutral_uncertain_count: int = 0
    baseline_mean_return_pct: float | None = None
    positive_mean_return_pct: float | None = None
    positive_minus_baseline_pct: float | None = None


class LLMRiskWarningMetric(StrictModel):
    high_risk_mean_drawdown_pct: float | None = None
    low_risk_mean_drawdown_pct: float | None = None
    causal_claim: Literal[False] = False


class LLMVersionMetric(LLMAggregateMetric):
    prompt_version_id: str
    model_version_id: str


class LLMSignalEvaluationReport(StrictModel):
    schema_version: Literal["3.4-evaluation-report"] = "3.4-evaluation-report"
    signal_fixture_checksum: str
    outcome_fixture_checksum: str
    evaluations: list[LLMSignalEvaluation]
    spillover_evaluations: list[LLMSpilloverEvaluation]
    horizon_metrics: dict[str, LLMAggregateMetric]
    confidence_metrics: dict[str, dict[str, LLMAggregateMetric]]
    risk_warning_metrics: dict[str, LLMRiskWarningMetric]
    spillover_metrics: dict[str, LLMAggregateMetric]
    version_metrics: dict[str, LLMVersionMetric]
    metadata_json: dict = Field(default_factory=lambda: dict(SAFETY_METADATA))
