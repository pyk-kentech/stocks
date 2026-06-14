from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
from stock_risk_mcp.models import StrictModel


class KiwoomAccountReadStatus(StrEnum):
    DISABLED = "DISABLED"
    PLANNED = "PLANNED"
    DRY_RUN = "DRY_RUN"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class KiwoomAccountReadConfig(StrictModel):
    enable_real_network: bool = False
    enable_account_read: bool = False
    environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK
    base_url: str = "https://mockapi.kiwoom.com"
    credential_source: KiwoomCredentialSource = KiwoomCredentialSource.NONE
    credential_file: Path | None = Field(default=None, repr=False)
    allow_auth_token_request: bool = False
    account_confirmed: bool = False
    account_fingerprint: str | None = None
    acknowledged_account_data_read: bool = False
    kill_switch_inactive: bool | None = None
    timeout_seconds: float = Field(default=10, gt=0, le=60)


class KiwoomAccountReadRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: f"kiwoom_account_request_{uuid4().hex}")
    run_id: str
    endpoint_id: str
    endpoint_path: str
    endpoint_classification: str = "ACCOUNT_READ"
    request_status: str
    sanitized_error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})


class KiwoomAccountReadResponse(StrictModel):
    response_id: str = Field(default_factory=lambda: f"kiwoom_account_response_{uuid4().hex}")
    request_id: str
    run_id: str
    endpoint_id: str
    response_status: str
    response_status_code: int | None = None
    normalized_summary_json: dict = Field(default_factory=dict)
    sanitized_error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})


class KiwoomAccountReadRun(StrictModel):
    run_id: str = Field(default_factory=lambda: f"kiwoom_account_run_{uuid4().hex}")
    status: KiwoomAccountReadStatus
    account_read_enabled: bool
    dry_run: bool = False
    environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK
    credential_source: KiwoomCredentialSource = KiwoomCredentialSource.NONE
    account_loaded: bool = False
    account_fingerprint: str | None = None
    endpoint_ids: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.now)
    requests: list[KiwoomAccountReadRequest] = Field(default_factory=list)
    responses: list[KiwoomAccountReadResponse] = Field(default_factory=list)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})


class KiwoomAccountReadReconcilePreview(StrictModel):
    preview_id: str = Field(default_factory=lambda: f"kiwoom_account_preview_{uuid4().hex}")
    run_id: str
    account_fingerprint: str | None = None
    reconciliation_status: str = "LOCAL_LEDGER_UNAVAILABLE"
    account_fingerprint_present: bool = False
    local_ledger_present: bool = False
    symbol_count_compared: int = 0
    missing_in_local_count: int = 0
    missing_in_account_count: int = 0
    quantity_mismatch_count: int = 0
    remote_symbol_count: int = 0
    local_symbol_count: int = 0
    mismatch_count: int = 0
    symbol_details_json: list[dict] = Field(default_factory=list)
    orders_submitted: bool = False
    live_execution_enabled: bool = False
    observed_at: datetime = Field(default_factory=datetime.now)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})


def sanitize_account_error(error: str | None) -> str | None:
    if error is None:
        return None
    lowered = error.lower()
    if any(item in lowered for item in ("token", "secret", "appkey", "authorization", "account_number", "bearer ")):
        return "sensitive error redacted"
    return error
