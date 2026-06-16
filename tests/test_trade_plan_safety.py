import ast
from pathlib import Path


def test_trade_plan_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "trade_plan_models.py",
        "trade_plan_fixture.py",
        "trade_plan_engine.py",
        "basket_risk_engine.py",
    )
    forbidden = ("database", "repository", "provider", "realtime", "broker", "kiwoom", "account", "order", "network", "requests", "httpx")
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "StrategyDecision(" not in text
        assert "OrderIntent(" not in text
