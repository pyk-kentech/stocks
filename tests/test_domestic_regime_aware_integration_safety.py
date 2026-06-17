import ast
from pathlib import Path

from stock_risk_mcp.domestic_regime_aware_integration_engine import (
    build_domestic_regime_aware_integration_report,
)
from stock_risk_mcp.domestic_regime_aware_integration_fixture import (
    load_domestic_regime_aware_integration_fixture,
)
from tests.test_domestic_regime_aware_integration_fixture import (
    regime_aware_integration_fixture_payload,
)
from tests.test_domestic_realtime_fixture import write


def test_domestic_regime_aware_integration_core_has_no_forbidden_imports_or_artifact_creation():
    root = Path(__file__).resolve().parents[1] / "src" / "stock_risk_mcp"
    files = (
        "domestic_regime_aware_integration_models.py",
        "domestic_regime_aware_integration_fixture.py",
        "domestic_regime_aware_integration_engine.py",
        "domestic_regime_aware_integration_service.py",
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
        "yfinance",
    )
    for name in files:
        text = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(term not in item.lower() for term in forbidden for item in imports)
        assert "OrderIntent(" not in text
        assert "create_order_intent_draft(" not in text


def test_domestic_regime_aware_integration_report_is_non_executable_and_uses_no_trade_labels(tmp_path):
    fixture = load_domestic_regime_aware_integration_fixture(
        write(
            tmp_path,
            "domestic_regime_aware_integration_fixture.json",
            regime_aware_integration_fixture_payload(tmp_path),
        )
    )
    report = build_domestic_regime_aware_integration_report(fixture)
    forbidden = {"BUY_MARKET", "SELL_MARKET", "ENTER_LONG", "EXIT_POSITION", "TRADE_APPROVED"}
    assert report.non_executable is True
    assert report.primary_regime_label.value not in forbidden
    assert all(label.value not in forbidden for label in report.secondary_regime_labels)
