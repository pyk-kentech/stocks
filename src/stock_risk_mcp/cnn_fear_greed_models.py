from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


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


def _validate_local_path(value: str, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local file path")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return cleaned


def _validate_safety_flags(model, context: str):
    for flag_name in (
        "report_only",
        "non_executable",
        "no_trading_path",
        "no_order",
        "no_account_mutation",
        "no_broker_api",
        "no_websocket",
        "no_cloud_llm",
        "no_local_llm_runtime",
    ):
        if not getattr(model, flag_name):
            raise ValueError(f"{context} must remain {flag_name}")
    return model


class CNNFearGreedCategory(StrEnum):
    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"
    UNKNOWN = "UNKNOWN"


class CNNFearGreedCollectionMode(StrEnum):
    MOCKED_HTTP = "MOCKED_HTTP"
    REAL_HTTP = "REAL_HTTP"


class CNNFearGreedGapCategory(StrEnum):
    COLLECTION_REPORT_GENERATED = "COLLECTION_REPORT_GENERATED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    SOURCE_HEALTH_WARNING = "SOURCE_HEALTH_WARNING"
    REAL_NETWORK_OPT_IN_REQUIRED = "REAL_NETWORK_OPT_IN_REQUIRED"
    HIGH_FREQUENCY_COLLECTION_NOT_ALLOWED = "HIGH_FREQUENCY_COLLECTION_NOT_ALLOWED"


class _CNNFearGreedBase(StrictModel):
    report_only: bool = True
    non_executable: bool = True
    no_trading_path: bool = True
    no_order: bool = True
    no_account_mutation: bool = True
    no_broker_api: bool = True
    no_websocket: bool = True
    no_cloud_llm: bool = True
    no_local_llm_runtime: bool = True


class CNNFearGreedSnapshot(_CNNFearGreedBase):
    score: int | None = Field(default=None, ge=0, le=100)
    category: CNNFearGreedCategory = CNNFearGreedCategory.UNKNOWN
    as_of: datetime | None = None
    available_at: datetime | None = None
    source_url: str = Field(..., min_length=1)
    collection_mode: CNNFearGreedCollectionMode
    component_scores: dict[str, int] = Field(default_factory=dict)
    observed_schema_version: str = Field(..., min_length=1)
    raw_payload_redacted: str = Field(..., min_length=1)

    @field_validator("as_of", "available_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)

    @field_validator("source_url", "observed_schema_version", "raw_payload_redacted", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_snapshot(self):
        return _validate_safety_flags(self, "cnn fear greed snapshot")


class CNNFearGreedHistoryPoint(StrictModel):
    as_of: datetime
    score: int = Field(..., ge=0, le=100)

    @field_validator("as_of", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        parsed = _aware(value)
        assert parsed is not None
        return parsed


class CNNFearGreedSnapshotReport(_CNNFearGreedBase):
    report_id: str = Field(..., min_length=1)
    snapshot: CNNFearGreedSnapshot

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "snapshot report")


class CNNFearGreedHistoryReport(_CNNFearGreedBase):
    report_id: str = Field(..., min_length=1)
    history_points: list[CNNFearGreedHistoryPoint] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "history report")


class CNNFearGreedFeatureIntegrationReport(_CNNFearGreedBase):
    report_id: str = Field(..., min_length=1)
    cnn_fear_greed_score: int | None = Field(default=None, ge=0, le=100)
    cnn_fear_greed_category: str = Field(..., min_length=1)
    cnn_fear_greed_available_at: str | None = None
    cnn_fear_greed_source_ref: str = Field(..., min_length=1)
    sentiment_fear_bucket: str = Field(..., min_length=1)

    @field_validator("report_id", "cnn_fear_greed_category", "cnn_fear_greed_source_ref", "sentiment_fear_bucket", mode="before")
    @classmethod
    def normalize_upper_or_string(cls, value, info):
        if info.field_name == "cnn_fear_greed_source_ref":
            return _string_required(value, info.field_name)
        return _upper_required(value, info.field_name)

    @field_validator("cnn_fear_greed_available_at", mode="before")
    @classmethod
    def normalize_optional_available_at(cls, value):
        if value is None:
            return None
        parsed = _aware(value)
        assert parsed is not None
        return parsed.isoformat()

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "feature integration report")


class CNNFearGreedSourceHealthReport(_CNNFearGreedBase):
    report_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    schema_mismatch_detected: bool = False
    warning_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("report_id", "status", mode="before")
    @classmethod
    def normalize_upper(cls, value):
        return _upper_required(value, "source_health")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "source health report")


class CNNFearGreedGapReport(_CNNFearGreedBase):
    gap_report_id: str = Field(..., min_length=1)
    gap_categories: list[CNNFearGreedGapCategory] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("gap_report_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "gap_report_id")

    @model_validator(mode="after")
    def validate_report(self):
        return _validate_safety_flags(self, "gap report")


class CNNFearGreedAuditRecord(_CNNFearGreedBase):
    audit_record_id: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    collection_mode: CNNFearGreedCollectionMode
    redaction_applied: bool = True
    contains_secret_material: bool = False
    raw_payload_sha256: str = Field(..., min_length=1)

    @field_validator("audit_record_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "audit_record_id")

    @field_validator("source_url", "raw_payload_sha256", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_report(self):
        if not self.redaction_applied or self.contains_secret_material:
            raise ValueError("audit record must remain redacted and secret-free")
        return _validate_safety_flags(self, "audit record")


class CNNFearGreedCollectorConfig(_CNNFearGreedBase):
    config_id: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    enabled: bool = False
    execute_collection: bool = False
    acknowledge_collection: bool = False
    allow_real_network: bool = False
    transport_mode: CNNFearGreedCollectionMode = CNNFearGreedCollectionMode.MOCKED_HTTP
    timeout_seconds: int = Field(default=5, ge=1, le=30)
    max_retry_count: int = Field(default=1, ge=0, le=3)
    max_requests_per_run: int = Field(default=1, ge=1, le=3)
    min_collection_interval_seconds: int = Field(default=3600, ge=0)
    cache_metadata_policy: str = Field(default="REPORT_ONLY", min_length=1)
    source_health_reporting: bool = True
    mock_payload: dict | list | str | None = None
    snapshot_report: CNNFearGreedSnapshotReport | None = None
    history_report: CNNFearGreedHistoryReport | None = None
    feature_integration_report: CNNFearGreedFeatureIntegrationReport | None = None
    source_health_report: CNNFearGreedSourceHealthReport | None = None
    gap_report: CNNFearGreedGapReport | None = None
    audit_report: CNNFearGreedAuditRecord | None = None

    @field_validator("config_id", mode="before")
    @classmethod
    def normalize_id(cls, value):
        return _upper_required(value, "config_id")

    @field_validator("source_url", "cache_metadata_policy", mode="before")
    @classmethod
    def normalize_string(cls, value, info):
        if info.field_name == "cache_metadata_policy":
            return _upper_required(value, info.field_name)
        return _string_required(value, info.field_name)

    @model_validator(mode="after")
    def validate_config(self):
        if self.transport_mode == CNNFearGreedCollectionMode.REAL_HTTP and not self.allow_real_network:
            raise ValueError("real transport mode requires allow_real_network=true")
        return _validate_safety_flags(self, "collector config")


def redact_payload(raw_payload) -> str:
    if isinstance(raw_payload, dict):
        summary = {"payload_type": "dict", "keys": sorted(raw_payload.keys())[:12]}
    elif isinstance(raw_payload, list):
        summary = {"payload_type": "list", "length": len(raw_payload)}
    else:
        text = str(raw_payload)
        summary = {"payload_type": "text", "preview": text[:120]}
    return json.dumps(summary, ensure_ascii=True, sort_keys=True)


def hash_payload(raw_payload) -> str:
    encoded = json.dumps(raw_payload, sort_keys=True, ensure_ascii=True).encode("utf-8") if not isinstance(raw_payload, str) else raw_payload.encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
