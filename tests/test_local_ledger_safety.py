from pathlib import Path


def test_local_ledger_and_sell_safety_are_not_wired_to_account_read_strategy_or_network():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    modules = [
        root / "local_ledger.py",
        root / "local_ledger_service.py",
        root / "sell_safety.py",
        root / "sell_safety_gate.py",
    ]
    forbidden = (
        "kiwoom_account_read", "strategy_optimizer", "kiwoom_sandbox_order_transport",
        "requests", "httpx", "urllib", "appkey", "secretkey", "authorization",
    )
    for module in modules:
        text = module.read_text(encoding="utf-8").lower()
        assert all(item not in text for item in forbidden)
