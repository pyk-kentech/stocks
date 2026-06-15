from pathlib import Path


def test_backtest_core_has_no_db_broker_account_order_credential_or_network_dependency() -> None:
    text = (Path(__file__).resolve().parents[1] / "src/stock_risk_mcp/strategy_backtest.py").read_text(encoding="utf-8").lower()
    forbidden = (
        "from stock_risk_mcp.repository", "import sqlite", "from stock_risk_mcp.broker",
        "from stock_risk_mcp.kiwoom", "from stock_risk_mcp.account", "from stock_risk_mcp.order",
        "load_kiwoom_credentials", "token_provider", "import requests", "import httpx",
        "import urllib", "urlopen",
    )
    assert all(item not in text for item in forbidden)


def test_backtest_fixture_and_service_have_no_forbidden_runtime_paths() -> None:
    root = Path(__file__).resolve().parents[1] / "src/stock_risk_mcp"
    fixture_text = (root / "strategy_backtest_fixture.py").read_text(encoding="utf-8").lower()
    service_text = (root / "strategy_backtest_service.py").read_text(encoding="utf-8").lower()
    assert all(item not in fixture_text for item in ("repository", "sqlite", "broker", "kiwoom", "account_read", "urlopen"))
    assert all(item not in service_text for item in ("broker", "kiwoom", "account_read", "order_intent", "credential", "urlopen"))
