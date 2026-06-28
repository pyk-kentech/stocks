from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class KiwoomCredentialSource(StrEnum):
    NONE = "NONE"
    ENV = "ENV"
    FILE_EXPLICIT = "FILE_EXPLICIT"


class KiwoomRealNetworkEnvironment(StrEnum):
    MOCK = "MOCK"
    REAL_READONLY = "REAL_READONLY"
    PROD_READONLY_DISABLED = "PROD_READONLY_DISABLED"


class KiwoomCredentials(StrictModel):
    appkey: str | None = Field(default=None, repr=False)
    secretkey: str | None = Field(default=None, repr=False)
    account_number: str | None = Field(default=None, repr=False)
    source: KiwoomCredentialSource = KiwoomCredentialSource.NONE
    loaded_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @property
    def loaded(self) -> bool:
        return bool(self.appkey and self.secretkey and not self.errors)

    def safe_summary(self) -> dict:
        return {"credential_source": self.source.value, "credentials_loaded": self.loaded}


class KiwoomRealNetworkConfig(StrictModel):
    enabled: bool = False
    environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK
    base_url: str = "https://mockapi.kiwoom.com"
    timeout_seconds: float = Field(default=10, gt=0, le=60)
    max_requests_per_run: int = Field(default=5, ge=1, le=20)
    allow_auth_token_request: bool = False
    credential_source: KiwoomCredentialSource = KiwoomCredentialSource.NONE
    credential_file: Path | None = Field(default=None, repr=False)
    redact_logs: bool = True


class KiwoomRealReadOnlyRun(StrictModel):
    run_id: str = Field(default_factory=lambda: f"kiwoom_real_run_{uuid4().hex}")
    enabled: bool
    credential_source: KiwoomCredentialSource
    status: str
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class KiwoomRealReadOnlyRequestAudit(StrictModel):
    request_id: str = Field(default_factory=lambda: f"kiwoom_real_request_{uuid4().hex}")
    run_id: str
    api_id: str
    path: str
    classification: str
    status: str
    error: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.now)


class KiwoomRealReadOnlyResponseAudit(StrictModel):
    response_id: str = Field(default_factory=lambda: f"kiwoom_real_response_{uuid4().hex}")
    request_id: str
    status: str
    error: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.now)
