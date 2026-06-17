import ast
from pathlib import Path

from stock_risk_mcp.domestic_distillation_dataset_engine import build_domestic_distillation_dataset_pack
from stock_risk_mcp.domestic_distillation_dataset_fixture import load_domestic_distillation_dataset_fixture
from tests.test_domestic_distillation_dataset_fixture import distillation_dataset_fixture_payload
from tests.test_domestic_realtime_fixture import write


def test_domestic_distillation_dataset_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "domestic_distillation_dataset_models.py",
        "domestic_distillation_dataset_fixture.py",
        "domestic_distillation_dataset_engine.py",
        "domestic_distillation_dataset_service.py",
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


def test_domestic_distillation_dataset_pack_uses_no_trade_execution_labels(tmp_path):
    fixture = load_domestic_distillation_dataset_fixture(
        write(tmp_path, "domestic_distillation_dataset_fixture.json", distillation_dataset_fixture_payload(tmp_path))
    )
    pack = build_domestic_distillation_dataset_pack(fixture)
    forbidden = {
        "BUY",
        "SELL",
        "ENTRY",
        "EXIT",
        "ORDER",
        "TRADE_SUCCESS",
        "PROFIT_TRADE",
        "LOSS_TRADE",
        "EXECUTION_RESULT",
        "APPROVED_ENTRY",
    }
    assert all(record.label_set.primary_label.value not in forbidden for record in pack.records)
