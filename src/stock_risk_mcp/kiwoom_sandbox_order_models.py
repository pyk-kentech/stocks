from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.order_intent import OrderSide, OrderType


class KiwoomSandboxOrderStatus(StrEnum):
    DISABLED = "DISABLED"
    PLANNED = "PLANNED"
    DRY_RUN = "DRY_RUN"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class KiwoomSandboxOrderConfig(StrictModel):
    enable_real_network: bool = False
    enable_sandbox_order: bool = False
    environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK
    base_url: str = "https://mockapi.kiwoom.com"
    credential_source: KiwoomCredentialSource = KiwoomCredentialSource.NONE
    credential_file: Path | None = Field(default=None, repr=False)
    allow_auth_token_request: bool = False
    timeout_seconds: float = Field(default=10, gt=0, le=60)


class KiwoomSandboxOrderPlan(StrictModel):
    intent_id: str
    risk_gate_status: str
    execution_gate_status: str
    order_type: OrderType
    side: OrderSide
    quantity: float | None
    limit_price: float | None
    stop_loss_present: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    would_submit: bool = False


class KiwoomSandboxOrderRun(StrictModel):
    run_id: str = Field(default_factory=lambda: f"kiwoom_sandbox_run_{uuid4().hex}")
    operation: str
    status: KiwoomSandboxOrderStatus
    enabled: bool
    environment: KiwoomRealNetworkEnvironment
    credential_source: KiwoomCredentialSource
    account_loaded: bool = False
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


class KiwoomSandboxOrderRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: f"kiwoom_sandbox_request_{uuid4().hex}")
    run_id: str
    intent_id: str
    client_order_id: str
    endpoint_id: str
    endpoint_path: str
    endpoint_classification: str = "ORDER"
    order_side: OrderSide
    order_type: OrderType
    quantity: int
    limit_price: float
    request_status: str
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


class KiwoomSandboxOrderReceipt(StrictModel):
    receipt_id: str = Field(default_factory=lambda: f"kiwoom_sandbox_receipt_{uuid4().hex}")
    request_id: str
    run_id: str
    intent_id: str
    client_order_id: str
    status: KiwoomSandboxOrderStatus
    success: bool
    broker_order_id: str | None = None
    response_status_code: int | None = None
    sanitized_error: str | None = None
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


class KiwoomSandboxOrderStatusCheck(StrictModel):
    status_check_id: str = Field(default_factory=lambda: f"kiwoom_sandbox_status_{uuid4().hex}")
    broker_order_id: str
    status: KiwoomSandboxOrderStatus
    observed_at: datetime = Field(default_factory=datetime.now)
    metadata_json: dict = Field(default_factory=dict)


def sanitize_sandbox_error(error: str | None) -> str | None:
    if error is None:
        return None
    if any(item in error.lower() for item in ("token", "secret", "appkey", "authorization", "account_number", "credential file:")):
        return "sensitive error redacted"
    return error
