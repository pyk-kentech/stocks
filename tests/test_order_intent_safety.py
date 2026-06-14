from pathlib import Path

from stock_risk_mcp.cli import build_command_parser
from stock_risk_mcp.order_intent import OrderSide
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from stock_risk_mcp.sell_safety import SellSafetyDecision, SellSafetyStatus
from tests.test_order_risk_gate import _intent


def test_sell_is_not_short_but_explicit_short_is_blocked() -> None:
    intent = _intent(side=OrderSide.SELL)
    sell_safety = SellSafetyDecision(
        order_intent_id=intent.order_intent_id, symbol=intent.ticker, status=SellSafetyStatus.APPROVED
    )
    assert evaluate_risk_gate(intent, RiskGateConfig(), sell_safety_decision=sell_safety).approved
    assert not evaluate_risk_gate(
        _intent(side=OrderSide.SELL, metadata_json={"short": True}), RiskGateConfig()
    ).approved


def test_execution_foundation_has_no_live_enable_real_broker_or_secret_read() -> None:
    help_text = build_command_parser().format_help()
    root = Path(__file__).resolve().parents[1]
    source_files = list((root / "src" / "stock_risk_mcp").glob("*.py"))

    assert "--enable-live-trading" not in help_text
    assert not list((root / "src" / "stock_risk_mcp").glob("*live_broker*.py"))
    assert all("api_key_kiwoom" not in path.read_text(encoding="utf-8") for path in source_files)
    for name in ("order_intent_service.py", "order_risk_gate.py", "execution_gate.py", "paper_execution.py"):
        assert "kiwoom_readonly" not in (root / "src" / "stock_risk_mcp" / name).read_text(encoding="utf-8")
