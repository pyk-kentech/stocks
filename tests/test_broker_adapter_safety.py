from pathlib import Path

from stock_risk_mcp.mock_broker_adapter import MockBrokerAdapter
from stock_risk_mcp.order_intent import ExecutionGateDecision, ExecutionMode, OrderIntentStatus
from stock_risk_mcp.paper_execution import create_paper_execution
from tests.test_order_risk_gate import _intent


def test_broker_modules_have_no_sdk_network_secret_or_strategy_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    modules = [
        root / "src" / "stock_risk_mcp" / name for name in (
            "broker_models.py", "broker_adapter.py", "mock_broker_adapter.py", "broker_adapter_service.py",
        )
    ]
    forbidden_imports = ("pykiwoom", "openapi", "alpaca", "ibkr", "polygon", "urllib", "httpx")
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert "api_key_kiwoom" not in text
        assert all(f"import {item}" not in text for item in forbidden_imports)
        assert all(f"from {item}" not in text for item in forbidden_imports)
        assert "import requests" not in text
        assert "from requests" not in text
    assert "broker_adapter" not in (root / "src" / "stock_risk_mcp" / "strategy_optimizer.py").read_text(encoding="utf-8")


def test_v29_paper_executor_remains_independent() -> None:
    intent = _intent(status=OrderIntentStatus.EXECUTION_APPROVED)
    decision = ExecutionGateDecision(
        order_intent_id=intent.order_intent_id, approved=True,
        execution_mode=ExecutionMode.PAPER, decision="APPROVED",
    )
    paper = create_paper_execution(intent, decision)
    assert paper.filled_price == 100
    assert MockBrokerAdapter().capabilities()
