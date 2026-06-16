import ast
from pathlib import Path


def test_paper_eval_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "paper_eval_models.py",
        "paper_eval_fixture.py",
        "paper_fill_engine.py",
        "paper_eval_engine.py",
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
