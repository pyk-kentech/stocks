from stock_risk_mcp.order_intent import OrderIntent, OrderSide
from stock_risk_mcp.sell_safety import SellSafetyDecision, SellSafetyStatus


class SellSafetyGate:
    def __init__(self, repository) -> None:
        self.repository = repository

    def evaluate(self, intent: OrderIntent, reconciliation_status: str | None = None) -> SellSafetyDecision:
        reasons = []
        quantity = intent.quantity
        position = self.repository.get_local_ledger_position(intent.ticker, intent.region)
        if intent.side != OrderSide.SELL:
            reasons.append("SELL_SIDE_REQUIRED")
        if quantity is None or not float(quantity).is_integer() or quantity <= 0:
            reasons.append("INVALID_SELL_QUANTITY")
        if position is None:
            reasons.append(
                "LOCAL_LEDGER_UNAVAILABLE"
                if not self.repository.list_local_ledger_positions(1)
                else "NO_LOCAL_POSITION"
            )
            available = None
        else:
            available = position.available_quantity
            if available <= 0:
                reasons.append("NO_LOCAL_POSITION")
            elif quantity is not None and quantity > available:
                reasons.append("INSUFFICIENT_LOCAL_POSITION")
        if reconciliation_status and reconciliation_status != "COMPLETED":
            reasons.append("RECONCILIATION_NOT_SAFE")
        status = (
            SellSafetyStatus.NEEDS_RECONCILIATION
            if "RECONCILIATION_NOT_SAFE" in reasons
            else SellSafetyStatus.BLOCKED if reasons else SellSafetyStatus.APPROVED
        )
        decision = SellSafetyDecision(
            order_intent_id=intent.order_intent_id, symbol=intent.ticker, status=status,
            requested_quantity=int(quantity) if quantity is not None and float(quantity).is_integer() else None,
            available_quantity=available, reconciliation_status=reconciliation_status, reasons_json=reasons,
        )
        self.repository.save_sell_safety_decision(decision)
        return decision
