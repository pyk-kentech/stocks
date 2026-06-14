from datetime import datetime
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadStatus
from stock_risk_mcp.models import StrictModel


class KiwoomAccountReadSmokeStep(StrictModel):
    smoke_step_id: str = Field(default_factory=lambda: f"kiwoom_account_smoke_step_{uuid4().hex}")
    smoke_run_id: str
    endpoint_id: str
    endpoint_classification: str = "ACCOUNT_READ"
    request_status: str
    response_status_code: int | None = None
    success: bool = False
    sanitized_error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})


class KiwoomAccountReadSmokeRun(StrictModel):
    smoke_run_id: str = Field(default_factory=lambda: f"kiwoom_account_smoke_{uuid4().hex}")
    account_read_run_id: str | None = None
    status: KiwoomAccountReadStatus
    dry_run: bool = False
    endpoint_set: str | None = None
    endpoint_ids: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    blocked_reasons: list[str] = Field(default_factory=list)
    steps: list[KiwoomAccountReadSmokeStep] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.now)
    redacted_metadata_json: dict = Field(default_factory=lambda: {"redacted": True})
