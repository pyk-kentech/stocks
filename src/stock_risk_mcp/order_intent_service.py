from __future__ import annotations

from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntent, OrderIntentStatus
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.paper_execution import create_paper_execution
from stock_risk_mcp.repository import RiskRepository


class OrderIntentService:
    def __init__(self, repository: RiskRepository) -> None:
        self.repository = repository

    def create(self, intent: OrderIntent) -> OrderIntent:
        self.repository.save_order_intent(intent)
        return intent

    def evaluate(
        self,
        order_intent_id: str,
        risk_config: RiskGateConfig,
        execution_mode: ExecutionMode,
    ) -> dict:
        intent = self.repository.get_order_intent(order_intent_id)
        try:
            watchlist_entry = self.repository.get_watchlist_entry(intent.ticker, intent.region)
        except LookupError:
            watchlist_entry = None
        risk = evaluate_risk_gate(intent, risk_config, watchlist_entry)
        self.repository.save_risk_gate_decision(risk)
        if not risk.approved:
            self.repository.update_order_intent_status(order_intent_id, OrderIntentStatus.RISK_BLOCKED)
            return {
                "intent": self.repository.get_order_intent(order_intent_id),
                "risk_decision": risk,
                "execution_decision": None,
            }
        self.repository.update_order_intent_status(order_intent_id, OrderIntentStatus.RISK_APPROVED)
        intent = self.repository.get_order_intent(order_intent_id)
        execution = evaluate_execution_gate(
            intent, risk, execution_mode, self.repository.has_paper_execution(order_intent_id)
        )
        self.repository.save_execution_gate_decision(execution)
        status = OrderIntentStatus.EXECUTION_APPROVED if execution.approved else OrderIntentStatus.EXECUTION_BLOCKED
        self.repository.update_order_intent_status(order_intent_id, status)
        return {
            "intent": self.repository.get_order_intent(order_intent_id),
            "risk_decision": risk,
            "execution_decision": execution,
        }

    def evaluate_many(
        self,
        risk_config: RiskGateConfig,
        execution_mode: ExecutionMode,
        order_intent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        intents = [self.repository.get_order_intent(order_intent_id)] if order_intent_id else self.repository.list_order_intents(
            status=OrderIntentStatus.CREATED, limit=limit
        )
        return [self.evaluate(intent.order_intent_id, risk_config, execution_mode) for intent in intents]

    def paper_execute(self, order_intent_id: str, fill_price: float | None = None) -> dict:
        intent = self.repository.get_order_intent(order_intent_id)
        decision = self.repository.get_latest_execution_gate_decision(order_intent_id)
        if decision is None:
            raise ValueError("execution gate decision not found")
        if self.repository.has_paper_execution(order_intent_id):
            duplicate = evaluate_execution_gate(
                intent, self.repository.get_latest_risk_gate_decision(order_intent_id),
                ExecutionMode.PAPER, True,
            )
            self.repository.save_execution_gate_decision(duplicate)
            raise ValueError("paper execution already exists")
        execution = create_paper_execution(intent, decision, fill_price)
        self.repository.save_paper_execution(execution)
        self.repository.update_order_intent_status(order_intent_id, OrderIntentStatus.PAPER_EXECUTED)
        return {"intent": self.repository.get_order_intent(order_intent_id), "paper_execution": execution}

    def paper_execute_many(
        self, order_intent_id: str | None = None, fill_price: float | None = None, limit: int = 100
    ) -> list[dict]:
        intents = [self.repository.get_order_intent(order_intent_id)] if order_intent_id else self.repository.list_order_intents(
            status=OrderIntentStatus.EXECUTION_APPROVED, limit=limit
        )
        results = []
        for intent in intents:
            try:
                results.append(self.paper_execute(intent.order_intent_id, fill_price))
            except ValueError as exc:
                results.append({"intent": intent, "error": str(exc)})
        return results
