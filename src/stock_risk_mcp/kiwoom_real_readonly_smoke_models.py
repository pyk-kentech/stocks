from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
from stock_risk_mcp.models import StrictModel


class KiwoomRealReadOnlySmokeStatus(StrEnum):
    PLANNED = "PLANNED"
    DRY_RUN = "DRY_RUN"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class KiwoomRealReadOnlySmokeStep(StrictModel):
    smoke_step_id: str = Field(default_factory=lambda: f"kiwoom_smoke_step_{uuid4().hex}")
    smoke_run_id: str
    endpoint_id: str
    endpoint_path: str
    endpoint_classification: str
    request_status: str
    response_status_code: int | None = None
    success: bool = False
    sanitized_error: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.now)


class KiwoomRealReadOnlySmokeRun(StrictModel):
    smoke_run_id: str = Field(default_factory=lambda: f"kiwoom_smoke_run_{uuid4().hex}")
    enabled: bool
    dry_run: bool
    environment: KiwoomRealNetworkEnvironment
    base_url_allowed: bool
    credential_source: KiwoomCredentialSource
    endpoint_set: str | None = None
    endpoint_ids: list[str] = Field(default_factory=list)
    status: KiwoomRealReadOnlySmokeStatus
    success_count: int = 0
    failure_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    steps: list[KiwoomRealReadOnlySmokeStep] = Field(default_factory=list)


_SENSITIVE_KEY_PARTS = ("secret", "token", "auth", "appkey", "account", "credential", "password")
_SENSITIVE_ERROR_PARTS = (
    "bearer ", "token", "secretkey", "appkey", "account_number", "password",
    "credential file:",
)


def sanitized_smoke_step(step: KiwoomRealReadOnlySmokeStep) -> KiwoomRealReadOnlySmokeStep:
    copy = step.model_copy(deep=True)
    copy.sanitized_error = _sanitize_error(copy.sanitized_error)
    copy.metadata_json = _sanitize_metadata(copy.metadata_json)
    return copy


def sanitized_smoke_run(run: KiwoomRealReadOnlySmokeRun) -> KiwoomRealReadOnlySmokeRun:
    copy = run.model_copy(deep=True)
    copy.errors = [_sanitize_error(item) or "sensitive error redacted" for item in copy.errors]
    copy.warnings = [_sanitize_error(item) or "sensitive warning redacted" for item in copy.warnings]
    copy.metadata_json = _sanitize_metadata(copy.metadata_json)
    copy.steps = [sanitized_smoke_step(item) for item in copy.steps]
    return copy


def _sanitize_error(value: str | None) -> str | None:
    if value is None:
        return None
    if value == "--allow-auth-token-request is required":
        return value
    if any(part in value.lower() for part in _SENSITIVE_ERROR_PARTS):
        return "sensitive error redacted"
    return value


def _sanitize_metadata(value):
    if isinstance(value, dict):
        return {
            str(key): _sanitize_metadata(item)
            for key, item in value.items()
            if not any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
        }
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, str) and any(part in value.lower() for part in _SENSITIVE_ERROR_PARTS):
        return "<redacted>"
    return value
