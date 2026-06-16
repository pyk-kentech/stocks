import ast
from pathlib import Path


def test_local_model_runtime_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "local_model_runtime_models.py",
        "local_model_runtime_fixture.py",
        "local_model_runtime_guard.py",
        "local_model_runtime_adapter.py",
        "local_model_runtime_engine.py",
    )
    forbidden = ("database", "repository", "provider", "realtime", "broker", "kiwoom", "account", "order", "network", "requests", "httpx", "urllib", "transformers")
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "StrategyDecision(" not in text
        assert "OrderIntent(" not in text
        assert "create_order_intent_draft(" not in text
        assert "ollama.chat(" not in text
        assert "llama_cpp" not in text
