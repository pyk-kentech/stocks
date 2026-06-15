from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_sell_schema import (
    SandboxSellDryRunDecision,
    SandboxSellDryRunStatus,
    SandboxSellSchemaVerificationStatus,
)
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide, OrderType
from stock_risk_mcp.sell_safety import SellSafetyStatus


class KiwoomSandboxSellDryRunService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def run(
        self,
        order_intent_id: str,
        environment: KiwoomRealNetworkEnvironment = KiwoomRealNetworkEnvironment.MOCK,
    ) -> SandboxSellDryRunDecision:
        intent = self.repository.get_order_intent(order_intent_id)
        schema = self.repository.get_latest_kiwoom_sandbox_sell_schema_report()
        sell_safety = self.repository.get_latest_sell_safety_decision(order_intent_id)
        risk = self.repository.get_latest_risk_gate_decision(order_intent_id)
        execution = self.repository.get_latest_execution_gate_decision(order_intent_id)
        position = self.repository.get_local_ledger_position(intent.ticker, intent.region)
        reasons = []
        reasons.append("SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23")
        if intent.side != OrderSide.SELL:
            reasons.append("SELL_ORDER_INTENT_REQUIRED")
        if intent.order_type != OrderType.LIMIT:
            reasons.append("LIMIT_ORDER_REQUIRED")
        if intent.quantity is None or intent.quantity <= 0 or not float(intent.quantity).is_integer():
            reasons.append("POSITIVE_INTEGER_QUANTITY_REQUIRED")
        if intent.limit_price is None or intent.limit_price <= 0:
            reasons.append("POSITIVE_LIMIT_PRICE_REQUIRED")
        if environment != KiwoomRealNetworkEnvironment.MOCK:
            reasons.append("MOCK_ENVIRONMENT_REQUIRED")
        metadata = intent.metadata_json
        if metadata.get("margin") or metadata.get("short") or str(metadata.get("instrument_type", "")).upper() in {
            "OPTION", "OPTIONS", "FUTURE", "FUTURES",
        }:
            reasons.append("MARGIN_SHORT_OPTIONS_FUTURES_DISABLED")
        try:
            if float(metadata.get("leverage", 1)) > 1:
                reasons.append("LEVERAGE_DISABLED")
        except (TypeError, ValueError):
            reasons.append("INVALID_LEVERAGE")
        if schema is None or schema.status != SandboxSellSchemaVerificationStatus.VERIFIED:
            reasons.append("SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED")
        if sell_safety is None or sell_safety.status != SellSafetyStatus.APPROVED:
            reasons.append("APPROVED_SELL_SAFETY_DECISION_REQUIRED")
        if risk is None or not risk.approved:
            reasons.append("APPROVED_RISK_GATE_DECISION_REQUIRED")
        if execution is None or not execution.approved or execution.execution_mode != ExecutionMode.SANDBOX:
            reasons.append("APPROVED_SANDBOX_EXECUTION_GATE_DECISION_REQUIRED")
        if position is None:
            reasons.append("LOCAL_LEDGER_POSITION_REQUIRED")
        elif intent.quantity is None or position.available_quantity < intent.quantity:
            reasons.append("INSUFFICIENT_LOCAL_LEDGER_QUANTITY")
        decision = SandboxSellDryRunDecision(
            order_intent_id=order_intent_id,
            status=SandboxSellDryRunStatus.BLOCKED if reasons else SandboxSellDryRunStatus.APPROVED_FOR_DRY_RUN,
            schema_report_id=schema.report_id if schema else None,
            reasons_json=list(dict.fromkeys(reasons)),
            planned_order_metadata_json={
                "ticker": intent.ticker,
                "region": intent.region.value,
                "side": intent.side.value,
                "order_type": intent.order_type.value,
                "quantity": intent.quantity,
                "limit_price": intent.limit_price,
                "environment": environment.value,
            },
        )
        self.repository.save_kiwoom_sandbox_sell_dry_run(decision)
        return decision
