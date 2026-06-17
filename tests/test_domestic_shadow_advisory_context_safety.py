import ast
from pathlib import Path

from stock_risk_mcp.domestic_shadow_advisory_context_engine import build_domestic_shadow_advisory_context_bundle
from stock_risk_mcp.domestic_shadow_advisory_context_fixture import load_domestic_shadow_advisory_context_fixture
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_advisory_context_fixture import shadow_advisory_context_fixture_payload


def test_domestic_shadow_advisory_context_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "domestic_shadow_advisory_context_models.py",
        "domestic_shadow_advisory_context_fixture.py",
        "domestic_shadow_advisory_context_engine.py",
        "domestic_shadow_advisory_context_service.py",
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
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "OrderIntent(" not in text
        assert "create_order_intent_draft(" not in text


def test_domestic_shadow_advisory_context_bundle_uses_no_trade_execution_labels(tmp_path):
    fixture = load_domestic_shadow_advisory_context_fixture(
        write(tmp_path, "domestic_shadow_advisory_context_fixture.json", shadow_advisory_context_fixture_payload(tmp_path))
    )
    bundle = build_domestic_shadow_advisory_context_bundle(fixture)
    forbidden = {
        "BUY_SIGNAL",
        "SELL_SIGNAL",
        "ENTRY_SIGNAL",
        "EXIT_SIGNAL",
        "ORDER_RECOMMENDATION",
        "EXECUTION_ADVICE",
        "TRADE_APPROVAL",
        "POSITION_OPEN",
        "POSITION_CLOSE",
    }
    assert all(item.evidence_type.value not in forbidden for item in bundle.evidence_items)
