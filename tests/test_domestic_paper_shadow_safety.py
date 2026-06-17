import ast
from pathlib import Path


def test_domestic_paper_shadow_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "domestic_paper_shadow_models.py",
        "domestic_paper_shadow_fixture.py",
        "domestic_paper_shadow_engine.py",
        "domestic_paper_shadow_service.py",
    )
    forbidden = (
        "database",
        "repository",
        "broker",
        "kiwoom_rest",
        "kiwoom_transport",
        "kiwoom_credentials",
        "account",
        "network",
        "requests",
        "httpx",
        "websocket",
        "transformers",
        "ollama",
        "llama_cpp",
    )
    forbidden_text = (
        "BUY",
        "SELL",
        "EXECUTE",
        "ENTRY_APPROVED",
        "TRADE_APPROVED",
        "POSITION_OPEN",
        "POSITION_CLOSE",
    )
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "OrderIntent(" not in text
        assert "create_order_intent_draft(" not in text
        assert all(term not in text for term in forbidden_text)
