from stock_risk_mcp.execution_gate import evaluate_execution_gate
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide, RiskGateDecision
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety import SellSafetyStatus
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_order_risk_gate import _intent


def test_sell_safety_blocks_missing_symbol_and_insufficient_position(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    gate = SellSafetyGate(repository)
    missing = gate.evaluate(_intent(side=OrderSide.SELL, quantity=1))
    LocalLedgerService(repository).upsert_position("AAPL", MarketRegion.US, 2, reserved_quantity=1)
    insufficient = gate.evaluate(_intent(side=OrderSide.SELL, quantity=2))

    assert missing.status == SellSafetyStatus.BLOCKED
    assert "LOCAL_LEDGER_UNAVAILABLE" in missing.reasons_json
    assert "INSUFFICIENT_LOCAL_POSITION" in insufficient.reasons_json
    another = gate.evaluate(_intent(ticker="MSFT", side=OrderSide.SELL, quantity=1))
    assert "NO_LOCAL_POSITION" in another.reasons_json


def test_sell_safety_approves_available_position_and_reconciliation_mismatch_blocks(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    LocalLedgerService(repository).upsert_position("AAPL", MarketRegion.US, 5, reserved_quantity=1)
    gate = SellSafetyGate(repository)
    approved = gate.evaluate(_intent(side=OrderSide.SELL, quantity=4))
    mismatch = gate.evaluate(
        _intent(side=OrderSide.SELL, quantity=1),
        reconciliation_status="COMPLETED_WITH_MISMATCHES",
    )

    assert approved.status == SellSafetyStatus.APPROVED
    assert approved.available_quantity == 4
    assert mismatch.status == SellSafetyStatus.NEEDS_RECONCILIATION


def test_explicit_unavailable_reconciliation_status_requires_reconciliation(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    LocalLedgerService(repository).upsert_position("AAPL", MarketRegion.US, 5)

    decision = SellSafetyGate(repository).evaluate(
        _intent(side=OrderSide.SELL, quantity=1),
        reconciliation_status="ACCOUNT_DETAILS_UNAVAILABLE",
    )

    assert decision.status == SellSafetyStatus.NEEDS_RECONCILIATION
    assert "RECONCILIATION_NOT_SAFE" in decision.reasons_json


def test_sell_risk_and_sandbox_execution_require_matching_approved_sell_safety(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = _intent(side=OrderSide.SELL, quantity=1)
    LocalLedgerService(repository).upsert_position("AAPL", MarketRegion.US, 2)
    sell_safety = SellSafetyGate(repository).evaluate(intent)

    assert not evaluate_risk_gate(intent, RiskGateConfig()).approved
    risk = evaluate_risk_gate(intent, RiskGateConfig(), sell_safety_decision=sell_safety)
    assert risk.approved
    assert not evaluate_execution_gate(intent, risk, ExecutionMode.SANDBOX, False, True).approved
    assert evaluate_execution_gate(
        intent, risk, ExecutionMode.SANDBOX, False, True, sell_safety_decision=sell_safety
    ).approved


def test_buy_behavior_is_unchanged_without_sell_safety():
    assert evaluate_risk_gate(_intent(), RiskGateConfig()).approved
