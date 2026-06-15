from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import uuid4

from pydantic import Field

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_core import StrategyCandidate, StrategyDecision, StrategyFeatureSnapshot


class LocalLLMReview(StrictModel):
    review_id: str = Field(default_factory=lambda: f"local_llm_review_{uuid4().hex}")
    run_id: str
    decision_id: str
    status: str = "DISABLED"
    summary: str = "Local LLM advisor disabled"
    advisory_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: {
        "advisory_only": True, "network_called": False, "can_create_orders": False,
        "can_approve_execution": False,
    })
    created_at: datetime = Field(default_factory=datetime.now)


class LocalLLMAdvisor(Protocol):
    def health(self) -> dict: ...

    def review(
        self, run_id: str, snapshot: StrategyFeatureSnapshot,
        candidate: StrategyCandidate, decision: StrategyDecision,
    ) -> LocalLLMReview: ...


class DisabledLocalLLMAdvisor:
    def health(self) -> dict:
        return {
            "status": "DISABLED", "network_called": False, "credentials_read": False,
            "account_data_read": False, "can_create_orders": False, "can_approve_execution": False,
        }

    def review(
        self, run_id: str, snapshot: StrategyFeatureSnapshot,
        candidate: StrategyCandidate, decision: StrategyDecision,
    ) -> LocalLLMReview:
        return LocalLLMReview(run_id=run_id, decision_id=decision.decision_id)
