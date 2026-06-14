from pathlib import Path

from stock_risk_mcp.cli import build_command_parser
from stock_risk_mcp.order_intent import OrderSide
from stock_risk_mcp.order_risk_gate import RiskGateConfig, evaluate_risk_gate
from tests.test_order_risk_gate import _intent


def test_sell_is_not_short_but_explicit_short_is_blocked() -> None:
    assert evaluate_risk_gate(_intent(side=OrderSide.SELL), RiskGateConfig()).approved
    assert not evaluate_risk_gate(
        _intent(side=OrderSide.SELL, metadata_json={"short": True}), RiskGateConfig()
    ).approved


def test_execution_foundation_has_no_live_enable_real_broker_or_secret_read() -> None:
    help_text = build_command_parser().format_help()
    root = Path(__file__).resolve().parents[1]
    source_files = list((root / "src" / "stock_risk_mcp").glob("*.py"))

    assert "--enable-live-trading" not in help_text
    assert not list((root / "src" / "stock_risk_mcp").glob("*kiwoom*.py"))
    assert not list((root / "src" / "stock_risk_mcp").glob("*live_broker*.py"))
    assert all("api_key_kiwoom" not in path.read_text(encoding="utf-8") for path in source_files)
