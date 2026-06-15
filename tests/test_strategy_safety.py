from pathlib import Path


def test_strategy_modules_have_no_forbidden_dependencies() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    modules = ("strategy_core.py", "strategy_fixture.py", "strategy_advisor.py")
    forbidden = (
        "import sqlite", "import requests", "import httpx", "import urllib", "urlopen",
        "os.environ", "from stock_risk_mcp.repository", "from stock_risk_mcp.broker",
        "from stock_risk_mcp.kiwoom", "from stock_risk_mcp.account_read",
        "from stock_risk_mcp.order_intent", "from stock_risk_mcp.execution_gate",
        "from stock_risk_mcp.order_risk_gate",
    )
    for name in modules:
        text = (root / name).read_text(encoding="utf-8").lower()
        assert all(item not in text for item in forbidden)
