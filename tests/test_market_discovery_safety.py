import ast
from pathlib import Path


def test_market_discovery_core_has_no_forbidden_dependencies_or_paths():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    names = (
        "market_discovery_models.py",
        "market_discovery_fixture.py",
        "market_discovery_scoring.py",
        "market_discovery_service.py",
    )
    forbidden = (
        "repository", "sqlite", "provider", "realtime", "broker", "kiwoom",
        "account", "order", "strategydecision", "strategy_decision",
        "credential", "token", "network", "urlopen", "requests", "httpx",
        "scrap", "prod", "live",
    )
    for name in names:
        text = (root / name).read_text(encoding="utf-8").lower()
        tree = ast.parse(text)
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ] + [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        assert all(item not in imported for item in forbidden for imported in imports)
        assert "strategydecision(" not in text
        assert "orderintent(" not in text
