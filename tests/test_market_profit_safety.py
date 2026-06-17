import ast
from pathlib import Path


def test_market_profit_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "market_profit_models.py",
        "market_profit_fixture.py",
        "market_profit_engine.py",
        "market_profit_service.py",
    )
    forbidden = ("database", "repository", "provider", "realtime", "broker", "kiwoom", "account", "order", "network", "requests", "httpx")
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "OrderIntent(" not in text
        assert "create_order_intent_draft(" not in text
