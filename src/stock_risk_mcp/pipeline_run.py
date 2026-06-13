from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class PipelineRunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NO_CANDIDATES = "NO_CANDIDATES"


class PipelineMode(StrEnum):
    SCAN_ONLY = "SCAN_ONLY"
    PAPER_BASKET = "PAPER_BASKET"
    REPLAY_EVALUATION = "REPLAY_EVALUATION"
    WATCH_ONCE = "WATCH_ONCE"
    WATCH_LOOP = "WATCH_LOOP"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(StrEnum):
    CANDIDATE_FOUND = "CANDIDATE_FOUND"
    BASKET_PROPOSED = "BASKET_PROPOSED"
    BASKET_BLOCKED = "BASKET_BLOCKED"
    PAPER_WIN = "PAPER_WIN"
    PAPER_LOSS = "PAPER_LOSS"
    POLICY_ACCEPT = "POLICY_ACCEPT"
    POLICY_REJECT = "POLICY_REJECT"
    NEED_MORE_DATA = "NEED_MORE_DATA"
    SIGNAL_CRITICAL = "SIGNAL_CRITICAL"
    PIPELINE_ERROR = "PIPELINE_ERROR"
    FX_WARNING = "FX_WARNING"


class PipelineRun(StrictModel):
    pipeline_run_id: str
    mode: PipelineMode
    as_of_date: date
    policy_id: str | None = None
    policy_version: str | None = None
    scan_run_id: str | None = None
    basket_id: str | None = None
    replay_run_id: str | None = None
    policy_replay_id: str | None = None
    evaluation_suite_id: str | None = None
    status: PipelineRunStatus
    candidate_count: int
    included_count: int
    watch_count: int
    basket_allocation_count: int
    alert_count: int
    notes: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    account_currency: str = "USD"
    trading_currency: str = "USD"
    fx_rate: float | None = 1.0
    fx_date: date | None = None
    fx_source_name: str | None = None
    fx_stale: bool = False
    account_equity_input: float | None = None
    cash_available_input: float | None = None
    account_equity_trading: float | None = None
    cash_available_trading: float | None = None
    fx_warnings_json: list[str] = Field(default_factory=list)


class PipelineAlert(StrictModel):
    alert_id: str
    pipeline_run_id: str
    alert_type: AlertType
    severity: AlertSeverity
    ticker: str | None = None
    title: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PipelineSummary(StrictModel):
    pipeline_run_id: str
    status: PipelineRunStatus
    as_of_date: date
    candidate_count: int
    included_count: int
    watch_count: int
    basket_decision: str | None = None
    basket_allocation_count: int
    paper_outcome: str | None = None
    realized_return_pct: float | None = None
    policy_recommendation: str | None = None
    alert_count: int
    top_alerts: list[PipelineAlert] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    account_currency: str = "USD"
    trading_currency: str = "USD"
    fx_rate: float | None = 1.0
    fx_date: date | None = None
    fx_source_name: str | None = None
    fx_stale: bool = False
    account_equity_input: float | None = None
    cash_available_input: float | None = None
    account_equity_trading: float | None = None
    cash_available_trading: float | None = None
    fx_warnings_json: list[str] = Field(default_factory=list)
