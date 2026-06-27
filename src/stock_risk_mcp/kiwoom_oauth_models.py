from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def _aware(value):
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


def _safe_local_path(value, field_name: str) -> str:
    cleaned = _string_required(value, field_name)
    lowered = cleaned.lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError(f"{field_name} must be a local path")
    return cleaned


class KiwoomEnvironment(StrEnum):
    MOCK = "MOCK"
    REAL = "REAL"


class KiwoomOAuthStatus(StrEnum):
    TOKEN_PREFLIGHT_READY = "TOKEN_PREFLIGHT_READY"
    TOKEN_ISSUED = "TOKEN_ISSUED"
    TOKEN_CACHE_HIT = "TOKEN_CACHE_HIT"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_REFRESH_REQUIRED = "TOKEN_REFRESH_REQUIRED"
    BLOCKED_CREDENTIAL_MISSING = "BLOCKED_CREDENTIAL_MISSING"
    BLOCKED_CREDENTIAL_FORMAT = "BLOCKED_CREDENTIAL_FORMAT"
    BLOCKED_TOKEN_ENDPOINT_CONFIG = "BLOCKED_TOKEN_ENDPOINT_CONFIG"
    BLOCKED_NETWORK_IN_TEST = "BLOCKED_NETWORK_IN_TEST"
    BLOCKED_REAL_OAUTH_OPT_IN_REQUIRED = "BLOCKED_REAL_OAUTH_OPT_IN_REQUIRED"
    PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
    PROVIDER_TOKEN_ERROR = "PROVIDER_TOKEN_ERROR"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    REJECTED = "REJECTED"


class KiwoomOAuthEndpointConfig(StrictModel):
    environment: KiwoomEnvironment
    base_url: str = Field(..., min_length=1)
    token_path: str = "/oauth2/token"
    content_type: str = "application/json;charset=UTF-8"
    timeout_seconds: int = Field(default=10, ge=1, le=60)

    @field_validator("base_url", "token_path", "content_type", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        return _string_required(value, info.field_name)


class KiwoomCredentialRef(StrictModel):
    credential_ref_dir: str | None = Field(default=None)
    appkey_ref_path: str | None = Field(default=None)
    secretkey_ref_path: str | None = Field(default=None)
    credential_id: str = Field(..., min_length=1)
    source_kind: str = Field(default="LOCAL_FILE_REF", min_length=1)

    @field_validator("credential_ref_dir", "appkey_ref_path", "secretkey_ref_path", mode="before")
    @classmethod
    def normalize_paths(cls, value, info):
        if value is None:
            return None
        return _safe_local_path(value, info.field_name)

    @field_validator("credential_id", "source_kind", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name).upper()

    @model_validator(mode="after")
    def validate_ref(self):
        has_dir = bool(self.credential_ref_dir)
        has_explicit = bool(self.appkey_ref_path and self.secretkey_ref_path)
        if not has_dir and not has_explicit:
            raise ValueError("credential ref requires directory or explicit appkey/secretkey paths")
        if (self.appkey_ref_path is None) != (self.secretkey_ref_path is None):
            raise ValueError("explicit credential ref paths require both appkey_ref_path and secretkey_ref_path")
        return self


class KiwoomOAuthTokenIssueRequest(StrictModel):
    environment: KiwoomEnvironment
    credential_ref: KiwoomCredentialRef
    grant_type: str = "client_credentials"
    endpoint: KiwoomOAuthEndpointConfig
    token_store_root: str = Field(..., min_length=1)
    allow_real_network: bool = False
    allow_token_issue: bool = False
    acknowledge_readonly_only: bool = False
    acknowledge_user_initiated: bool = False
    acknowledge_credential_redaction: bool = False
    force_refresh_token: bool = False

    @field_validator("grant_type", "token_store_root", mode="before")
    @classmethod
    def normalize_strings(cls, value, info):
        if info.field_name == "token_store_root":
            return _safe_local_path(value, "token_store_root")
        return _string_required(value, info.field_name)


class KiwoomOAuthTokenRef(StrictModel):
    token_ref_path: str = Field(..., min_length=1)
    token_type: str = Field(..., min_length=1)
    expires_dt: str | None = None
    issued_at: datetime
    environment: KiwoomEnvironment
    credential_fingerprint_redacted: str = Field(..., min_length=1)

    @field_validator("token_ref_path", mode="before")
    @classmethod
    def normalize_path(cls, value):
        return _safe_local_path(value, "token_ref_path")

    @field_validator("token_type", "credential_fingerprint_redacted", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("issued_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class KiwoomOAuthTokenIssueResponse(StrictModel):
    status: KiwoomOAuthStatus
    token_type: str | None = None
    token_ref: KiwoomOAuthTokenRef | None = None
    expires_dt: str | None = None
    return_code: int | None = None
    return_msg_redacted: str = ""
    issued_at: datetime
    expires_at: datetime | None = None
    redaction_status: str = "PASSED"

    @field_validator("token_type", "return_msg_redacted", "redaction_status", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value, info):
        if value is None and info.field_name == "token_type":
            return None
        return _string_required(value, info.field_name)

    @field_validator("issued_at", "expires_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        if value is None:
            return None
        return _aware(value)


class KiwoomOAuthStoredToken(StrictModel):
    token: str = Field(..., min_length=1, repr=False)
    token_type: str = Field(..., min_length=1)
    expires_dt: str | None = None
    issued_at: datetime
    environment: KiwoomEnvironment
    credential_fingerprint_redacted: str = Field(..., min_length=1)

    @field_validator("token_type", "credential_fingerprint_redacted", mode="before")
    @classmethod
    def normalize_text(cls, value, info):
        return _string_required(value, info.field_name)

    @field_validator("issued_at", mode="before")
    @classmethod
    def normalize_dt(cls, value):
        return _aware(value)


class KiwoomOAuthPreflightReport(StrictModel):
    status: KiwoomOAuthStatus
    environment: KiwoomEnvironment
    credential_ref_present: bool = False
    token_store_root: str = Field(..., min_length=1)
    endpoint_base_url: str = Field(..., min_length=1)
    endpoint_path: str = Field(..., min_length=1)
    findings: list[str] = Field(default_factory=list)

    @field_validator("token_store_root", mode="before")
    @classmethod
    def normalize_root(cls, value):
        return _safe_local_path(value, "token_store_root")

    @field_validator("endpoint_base_url", "endpoint_path", mode="before")
    @classmethod
    def normalize_endpoint(cls, value, info):
        return _string_required(value, info.field_name)
